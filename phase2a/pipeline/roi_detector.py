"""
Interactive ROI-based detection using Grounding DINO + SAM.

Allows drawing polygons around areas of interest, then detecting
specific features within those regions.
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import logging
import json

logger = logging.getLogger(__name__)

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    from matplotlib.widgets import Button, CheckButtons
    from matplotlib.path import Path as MplPath
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

from .grounding_dino import GroundingDinoDetector
from .masks import MaskGenerator, MaskData


class InteractiveROIDetector:
    """
    Interactive polygon-based ROI detection with Grounding DINO + SAM.
    
    Usage:
        detector = InteractiveROIDetector(
            image=img,
            dino_checkpoint="models/groundingdino_swint_ogc.pth",
            sam_checkpoint="models/sam_vit_b_01ec64.pth",
        )
        results = detector.run()
    """
    
    FEATURE_TYPES = ["green", "bunker", "fairway", "tee", "water", "rough"]
    
    def __init__(
        self,
        image: np.ndarray,
        dino_checkpoint: str,
        sam_checkpoint: str,
        device: str = "cuda",
        model_type: str = "vit_b",
        output_dir: Optional[Path] = None,
        box_threshold: float = 0.25,
        text_threshold: float = 0.20,
    ):
        if not MATPLOTLIB_AVAILABLE:
            raise ImportError("matplotlib is required for interactive detection")
        
        self.image = image
        self.dino_checkpoint = dino_checkpoint
        self.sam_checkpoint = sam_checkpoint
        self.device = device
        self.model_type = model_type
        self.output_dir = Path(output_dir) if output_dir else Path("phase2a_output")
        self.box_threshold = box_threshold
        self.text_threshold = text_threshold
        
        # State
        self.current_hole = 1
        self.polygon_points: List[Tuple[int, int]] = []
        self.all_results: Dict[int, Dict[str, List[MaskData]]] = {}
        self.selected_features: List[str] = ["green", "bunker"]  # Default selection
        
        # Models (lazy loaded)
        self._detector = None
        self._sam = None
        
        # UI elements
        self.fig = None
        self.ax = None
        self.polygon_patch = None
        self.point_plots = []
        self._done = False
        
        # Pan/zoom state
        self._pan_start = None
        self._is_panning = False
    
    @property
    def detector(self) -> GroundingDinoDetector:
        if self._detector is None:
            logger.info(f"Loading Grounding DINO (box_thresh={self.box_threshold}, text_thresh={self.text_threshold})...")
            self._detector = GroundingDinoDetector(
                checkpoint_path=self.dino_checkpoint,
                device=self.device,
                box_threshold=self.box_threshold,
                text_threshold=self.text_threshold,
            )
        return self._detector
    
    @property
    def sam(self) -> MaskGenerator:
        if self._sam is None:
            logger.info(f"Loading SAM ({self.model_type})...")
            self._sam = MaskGenerator(
                checkpoint_path=self.sam_checkpoint,
                device=self.device,
                model_type=self.model_type,
            )
        return self._sam
    
    def _clear_dino_memory(self):
        """Clear DINO from GPU to make room for SAM."""
        if self._detector is not None and self._detector._model is not None:
            import torch
            del self._detector._model
            self._detector._model = None
            self._detector = None
            torch.cuda.empty_cache()
            logger.info("Cleared DINO from GPU memory")
    
    def _merge_overlapping_masks(self, masks: List[MaskData], feature_type: str) -> List[MaskData]:
        """Merge masks that overlap significantly (>50% IoU)."""
        if len(masks) <= 1:
            return masks
        
        # Calculate IoU between all pairs and merge overlapping ones
        merged = []
        used = set()
        
        for i, mask1 in enumerate(masks):
            if i in used:
                continue
            
            # Start with this mask
            combined_mask = mask1.mask.copy()
            used.add(i)
            
            # Find all overlapping masks
            for j, mask2 in enumerate(masks):
                if j in used or j <= i:
                    continue
                
                # Calculate overlap
                intersection = np.sum(mask1.mask & mask2.mask)
                union = np.sum(mask1.mask | mask2.mask)
                
                if union > 0:
                    iou = intersection / union
                    # Also check if one is mostly inside the other
                    overlap_ratio = intersection / min(np.sum(mask1.mask), np.sum(mask2.mask))
                    
                    if iou > 0.3 or overlap_ratio > 0.5:
                        # Merge - take union of masks
                        combined_mask = combined_mask | mask2.mask
                        used.add(j)
            
            # Create merged mask data
            merged_data = MaskData(
                id=f"{feature_type}_{self.current_hole}_{len(merged):04d}",
                mask=combined_mask,
                area=int(np.sum(combined_mask)),
                bbox=self._get_bbox(combined_mask),
                predicted_iou=mask1.predicted_iou if hasattr(mask1, 'predicted_iou') else 1.0,
                stability_score=mask1.stability_score if hasattr(mask1, 'stability_score') else 1.0,
            )
            merged.append(merged_data)
        
        logger.info(f"Merged {len(masks)} masks into {len(merged)} for {feature_type}")
        return merged
    
    def _get_bbox(self, mask: np.ndarray) -> Tuple[int, int, int, int]:
        """Get bounding box (x, y, w, h) from mask."""
        rows = np.any(mask, axis=1)
        cols = np.any(mask, axis=0)
        if not np.any(rows) or not np.any(cols):
            return (0, 0, 0, 0)
        y_min, y_max = np.where(rows)[0][[0, -1]]
        x_min, x_max = np.where(cols)[0][[0, -1]]
        return (int(x_min), int(y_min), int(x_max - x_min), int(y_max - y_min))
    
    def run(self) -> Dict[str, List[MaskData]]:
        """Run interactive detection. Returns all detected masks."""
        self._setup_ui()
        plt.show()
        
        # Flatten results by feature type
        all_masks: Dict[str, List[MaskData]] = {}
        for hole_num, hole_results in self.all_results.items():
            for feature_type, masks in hole_results.items():
                if feature_type not in all_masks:
                    all_masks[feature_type] = []
                all_masks[feature_type].extend(masks)
        
        # Save results
        self._save_results()
        
        return all_masks
    
    def _setup_ui(self):
        """Set up the matplotlib UI."""
        self.fig, self.ax = plt.subplots(1, 1, figsize=(14, 10))
        self.fig.canvas.manager.set_window_title(f"Hole {self.current_hole} - Draw polygon around hole area")
        
        # Show image
        self.ax.imshow(self.image)
        self._original_xlim = self.ax.get_xlim()
        self._original_ylim = self.ax.get_ylim()
        self.ax.set_title(
            f"Hole {self.current_hole}: Click to draw polygon | Scroll=Zoom | Middle-drag=Pan\n"
            "Right-click or Enter to close polygon | Esc to clear | 'r' to reset view",
            fontsize=11
        )
        
        # Create buttons
        ax_detect = plt.axes([0.05, 0.02, 0.10, 0.04])
        ax_clear = plt.axes([0.16, 0.02, 0.10, 0.04])
        ax_reset = plt.axes([0.27, 0.02, 0.10, 0.04])
        ax_next = plt.axes([0.38, 0.02, 0.10, 0.04])
        ax_done = plt.axes([0.49, 0.02, 0.10, 0.04])
        
        self.btn_detect = Button(ax_detect, 'Detect')
        self.btn_clear = Button(ax_clear, 'Clear')
        self.btn_reset = Button(ax_reset, 'Reset View')
        self.btn_next = Button(ax_next, 'Next Hole')
        self.btn_done = Button(ax_done, 'Done')
        
        self.btn_detect.on_clicked(self._on_detect)
        self.btn_clear.on_clicked(self._on_clear)
        self.btn_reset.on_clicked(self._on_reset_view)
        self.btn_next.on_clicked(self._on_next_hole)
        self.btn_done.on_clicked(self._on_done)
        
        # Feature checkboxes
        ax_check = plt.axes([0.70, 0.02, 0.25, 0.15])
        ax_check.set_title("Features to detect:", fontsize=10)
        self.check_buttons = CheckButtons(
            ax_check,
            self.FEATURE_TYPES,
            [f in self.selected_features for f in self.FEATURE_TYPES]
        )
        self.check_buttons.on_clicked(self._on_feature_toggle)
        
        # Connect events
        self.fig.canvas.mpl_connect('button_press_event', self._on_click)
        self.fig.canvas.mpl_connect('button_release_event', self._on_release)
        self.fig.canvas.mpl_connect('motion_notify_event', self._on_motion)
        self.fig.canvas.mpl_connect('scroll_event', self._on_scroll)
        self.fig.canvas.mpl_connect('key_press_event', self._on_key)
        
        plt.subplots_adjust(bottom=0.2)
    
    def _on_scroll(self, event):
        """Handle scroll wheel for zoom."""
        if event.inaxes != self.ax:
            return
        
        # Get current axis limits
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        
        # Get mouse position
        xdata, ydata = event.xdata, event.ydata
        
        # Zoom factor
        base_scale = 1.2
        if event.button == 'up':
            scale = 1 / base_scale  # Zoom in
        elif event.button == 'down':
            scale = base_scale  # Zoom out
        else:
            return
        
        # Calculate new limits centered on mouse position
        new_width = (xlim[1] - xlim[0]) * scale
        new_height = (ylim[1] - ylim[0]) * scale
        
        # Keep mouse position fixed
        relx = (xdata - xlim[0]) / (xlim[1] - xlim[0])
        rely = (ydata - ylim[0]) / (ylim[1] - ylim[0])
        
        new_xlim = [xdata - new_width * relx, xdata + new_width * (1 - relx)]
        new_ylim = [ydata - new_height * rely, ydata + new_height * (1 - rely)]
        
        self.ax.set_xlim(new_xlim)
        self.ax.set_ylim(new_ylim)
        self.fig.canvas.draw_idle()
    
    def _on_release(self, event):
        """Handle mouse button release."""
        if event.button == 2:  # Middle button release
            self._is_panning = False
            self._pan_start = None
    
    def _on_motion(self, event):
        """Handle mouse motion for panning."""
        if not self._is_panning or event.inaxes != self.ax:
            return
        
        if self._pan_start is None:
            return
        
        # Calculate pan distance
        dx = self._pan_start[0] - event.xdata
        dy = self._pan_start[1] - event.ydata
        
        # Get current limits
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        
        # Apply pan
        self.ax.set_xlim(xlim[0] + dx, xlim[1] + dx)
        self.ax.set_ylim(ylim[0] + dy, ylim[1] + dy)
        
        self.fig.canvas.draw_idle()
    
    def _on_click(self, event):
        """Handle mouse clicks for polygon drawing and panning."""
        if event.inaxes != self.ax:
            return
        
        if event.button == 1:  # Left click - add point
            x, y = int(event.xdata), int(event.ydata)
            self.polygon_points.append((x, y))
            self._update_polygon_display()
        
        elif event.button == 2:  # Middle click - start pan
            self._is_panning = True
            self._pan_start = (event.xdata, event.ydata)
        
        elif event.button == 3:  # Right click - close polygon
            if len(self.polygon_points) >= 3:
                self._close_polygon()
    
    def _on_key(self, event):
        """Handle keyboard events."""
        if event.key == 'enter' or event.key == 'return':
            if len(self.polygon_points) >= 3:
                self._close_polygon()
        elif event.key == 'escape':
            self._on_clear(None)
        elif event.key == 'r':
            self._on_reset_view(None)
    
    def _on_reset_view(self, event):
        """Reset zoom/pan to original view."""
        self.ax.set_xlim(self._original_xlim)
        self.ax.set_ylim(self._original_ylim)
        self.fig.canvas.draw_idle()
    
    def _update_polygon_display(self):
        """Update the polygon visualization."""
        # Clear previous points
        for p in self.point_plots:
            p.remove()
        self.point_plots = []
        
        if self.polygon_patch:
            self.polygon_patch.remove()
            self.polygon_patch = None
        
        if not self.polygon_points:
            self.fig.canvas.draw_idle()
            return
        
        # Draw points
        xs = [p[0] for p in self.polygon_points]
        ys = [p[1] for p in self.polygon_points]
        plot, = self.ax.plot(xs, ys, 'ro-', markersize=8, linewidth=2)
        self.point_plots.append(plot)
        
        # Draw closing line if enough points
        if len(self.polygon_points) >= 3:
            plot2, = self.ax.plot(
                [xs[-1], xs[0]], [ys[-1], ys[0]],
                'r--', linewidth=1, alpha=0.5
            )
            self.point_plots.append(plot2)
        
        self.fig.canvas.draw_idle()
    
    def _close_polygon(self):
        """Close the polygon and show it filled."""
        if len(self.polygon_points) < 3:
            return
        
        # Clear points display
        for p in self.point_plots:
            p.remove()
        self.point_plots = []
        
        # Draw filled polygon
        polygon = patches.Polygon(
            self.polygon_points,
            fill=True,
            facecolor='yellow',
            edgecolor='red',
            alpha=0.3,
            linewidth=2
        )
        self.polygon_patch = self.ax.add_patch(polygon)
        
        self.ax.set_title(
            f"Hole {self.current_hole}: Polygon defined - Click 'Detect' to find features",
            fontsize=12
        )
        self.fig.canvas.draw_idle()
    
    def _on_feature_toggle(self, label):
        """Handle feature checkbox toggle."""
        if label in self.selected_features:
            self.selected_features.remove(label)
        else:
            self.selected_features.append(label)
    
    def _on_detect(self, event):
        """Run detection within the polygon."""
        if len(self.polygon_points) < 3:
            self.ax.set_title("Draw a polygon first (at least 3 points)", fontsize=12, color='red')
            self.fig.canvas.draw_idle()
            return
        
        if not self.selected_features:
            self.ax.set_title("Select at least one feature type to detect", fontsize=12, color='red')
            self.fig.canvas.draw_idle()
            return
        
        self.ax.set_title(f"Detecting {', '.join(self.selected_features)}...", fontsize=12)
        self.fig.canvas.draw_idle()
        self.fig.canvas.flush_events()
        
        # Get bounding box of polygon for cropping
        xs = [p[0] for p in self.polygon_points]
        ys = [p[1] for p in self.polygon_points]
        x_min, x_max = max(0, min(xs)), min(self.image.shape[1], max(xs))
        y_min, y_max = max(0, min(ys)), min(self.image.shape[0], max(ys))
        
        # Crop image to polygon bounding box (with padding)
        pad = 50
        x_min_pad = max(0, x_min - pad)
        y_min_pad = max(0, y_min - pad)
        x_max_pad = min(self.image.shape[1], x_max + pad)
        y_max_pad = min(self.image.shape[0], y_max + pad)
        
        cropped = self.image[y_min_pad:y_max_pad, x_min_pad:x_max_pad]
        
        # Run DINO detection on cropped region
        logger.info(f"Running DINO on {cropped.shape[1]}x{cropped.shape[0]} region...")
        detections = self.detector.detect_golf_features(cropped, self.selected_features)
        
        total_boxes = sum(len(boxes) for boxes in detections.values())
        logger.info(f"DINO found {total_boxes} detections")
        
        # Clear DINO, load SAM
        self._clear_dino_memory()
        
        # Run SAM segmentation for each detection using POINT prompts (more precise than box)
        results: Dict[str, List[MaskData]] = {}
        mask_idx = 0
        
        # Create polygon mask for filtering
        polygon_path = MplPath(self.polygon_points)
        yy, xx = np.mgrid[:self.image.shape[0], :self.image.shape[1]]
        points = np.column_stack([xx.ravel(), yy.ravel()])
        inside_polygon = polygon_path.contains_points(points).reshape(self.image.shape[:2])
        
        for feature_type, boxes in detections.items():
            masks = []
            for box in boxes:
                # Use CENTER POINT of detection box (more precise than box prompt)
                x1, y1, x2, y2 = box.bbox
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                
                # Run SAM with point prompt for precise boundary detection
                mask_data = self.sam.generate_from_point(
                    cropped, 
                    point=(center_x, center_y),
                    label=1  # Foreground point
                )
                
                if mask_data:
                    # Adjust mask back to full image coordinates
                    full_mask = np.zeros(self.image.shape[:2], dtype=bool)
                    full_mask[y_min_pad:y_max_pad, x_min_pad:x_max_pad] = mask_data.mask
                    
                    # Filter by polygon - only keep mask pixels inside user's polygon
                    full_mask = full_mask & inside_polygon
                    
                    if np.any(full_mask):
                        mask_data.mask = full_mask
                        mask_data.id = f"{feature_type}_{self.current_hole}_{mask_idx:04d}"
                        mask_data.area = int(np.sum(full_mask))
                        masks.append(mask_data)
                        mask_idx += 1
            
            # Merge overlapping masks of same feature type
            if masks:
                merged_masks = self._merge_overlapping_masks(masks, feature_type)
                results[feature_type] = merged_masks
        
        # Store results
        self.all_results[self.current_hole] = results
        
        # Display results
        self._display_results(results)
        
        total_masks = sum(len(m) for m in results.values())
        self.ax.set_title(
            f"Hole {self.current_hole}: Found {total_masks} masks - "
            f"Click 'Next Hole' or 'Done'",
            fontsize=12, color='green'
        )
        self.fig.canvas.draw_idle()
    
    def _display_results(self, results: Dict[str, List[MaskData]]):
        """Overlay detected masks on the image."""
        # Save current view
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        
        # Create overlay
        overlay = self.image.copy().astype(float)
        
        # Color map for features
        colors = {
            "green": [0, 255, 0],
            "bunker": [255, 255, 150],
            "fairway": [100, 200, 100],
            "tee": [0, 200, 150],
            "water": [0, 100, 255],
            "rough": [50, 100, 50],
        }
        
        for feature_type, masks in results.items():
            color = np.array(colors.get(feature_type, [200, 200, 200]))
            for mask_data in masks:
                mask = mask_data.mask
                overlay[mask] = overlay[mask] * 0.5 + color * 0.5
        
        self.ax.clear()
        self.ax.imshow(overlay.astype(np.uint8))
        self.ax.set_xlim(xlim)
        self.ax.set_ylim(ylim)
        
        # Redraw polygon outline
        if self.polygon_points:
            polygon = patches.Polygon(
                self.polygon_points,
                fill=False,
                edgecolor='red',
                linewidth=2
            )
            self.polygon_patch = self.ax.add_patch(polygon)
    
    def _on_clear(self, event):
        """Clear current polygon (preserves zoom level)."""
        # Save current view
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        
        # Clear state
        self.polygon_points = []
        self.point_plots = []
        self.polygon_patch = None
        
        # Clear and redraw axes (this removes all artists)
        self.ax.clear()
        self.ax.imshow(self.image)
        self.ax.set_xlim(xlim)
        self.ax.set_ylim(ylim)
        self.ax.set_title(
            f"Hole {self.current_hole}: Click to draw polygon | Scroll=Zoom | Middle-drag=Pan\n"
            "Right-click or Enter to close polygon | Esc to clear | 'r' to reset view",
            fontsize=11
        )
        self.fig.canvas.draw_idle()
        self.fig.canvas.flush_events()
    
    def _on_next_hole(self, event):
        """Move to next hole."""
        self.current_hole += 1
        if self.current_hole > 18:
            self.current_hole = 18
            self.ax.set_title("All 18 holes complete! Click 'Done' to finish.", fontsize=12)
        else:
            self._on_clear(None)
            self.fig.canvas.manager.set_window_title(f"Hole {self.current_hole} - Draw polygon around hole area")
    
    def _on_done(self, event):
        """Finish and close."""
        self._done = True
        plt.close(self.fig)
    
    def _save_results(self):
        """Save detection results to files."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save metadata
        metadata = {
            "holes": {}
        }
        
        for hole_num, results in self.all_results.items():
            hole_data = {}
            for feature_type, masks in results.items():
                hole_data[feature_type] = [
                    {"id": m.id, "area": m.area}
                    for m in masks
                ]
            metadata["holes"][str(hole_num)] = hole_data
        
        metadata_path = self.output_dir / "roi_detections.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Saved detection metadata to {metadata_path}")
