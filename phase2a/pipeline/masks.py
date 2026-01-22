"""
Mask Generation Module

Generates candidate masks using SAM (Segment Anything Model)
automatic mask generation.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Any
import logging

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class MaskData:
    """Container for a single mask and its metadata."""
    id: str
    mask: np.ndarray
    area: int
    bbox: tuple  # (x, y, w, h)
    predicted_iou: float
    stability_score: float
    
    def to_dict(self) -> dict:
        """Export metadata to dictionary (excludes mask array)."""
        return {
            "id": self.id,
            "area": self.area,
            "bbox": list(self.bbox),
            "predicted_iou": self.predicted_iou,
            "stability_score": self.stability_score,
        }


class MaskGenerator:
    """
    Generate candidate masks using SAM automatic mask generation.
    
    This class wraps SAM's automatic mask generator to produce
    candidate masks from satellite imagery.
    """
    
    def __init__(
        self,
        model_type: str = "vit_h",
        checkpoint_path: Optional[str] = None,
        device: str = "cuda",
        points_per_side: int = 32,
        pred_iou_thresh: float = 0.88,
        stability_score_thresh: float = 0.95,
        min_mask_region_area: int = 100,
        point_mask_box_size: Optional[int] = None,  # Box size for point-based masks
    ):
        """
        Initialize the mask generator.
        
        Args:
            model_type: SAM model variant ('vit_h', 'vit_l', 'vit_b')
            checkpoint_path: Path to SAM checkpoint file
            device: Device to run inference on ('cuda' or 'cpu')
            points_per_side: Number of points per side for grid sampling
            pred_iou_thresh: Predicted IoU threshold for filtering
            stability_score_thresh: Stability score threshold
            min_mask_region_area: Minimum mask area in pixels
        """
        self.model_type = model_type
        self.checkpoint_path = checkpoint_path
        self.device = device
        self.points_per_side = points_per_side
        self.pred_iou_thresh = pred_iou_thresh
        self.stability_score_thresh = stability_score_thresh
        self.min_mask_region_area = min_mask_region_area
        self.point_mask_box_size = point_mask_box_size
        
        self._sam = None
        self._mask_generator = None
        self._predictor = None
    
    def _load_model(self) -> None:
        """Lazy-load SAM model."""
        if self._sam is not None:
            return
        
        try:
            import torch
            from segment_anything import sam_model_registry, SamAutomaticMaskGenerator, SamPredictor
        except ImportError:
            raise ImportError(
                "segment-anything is required for mask generation. "
                "Install with: pip install git+https://github.com/facebookresearch/segment-anything.git"
            )
        
        if self.checkpoint_path is None:
            raise ValueError(
                "SAM checkpoint path is required. Download from: "
                "https://github.com/facebookresearch/segment-anything#model-checkpoints"
            )
        
        logger.info(f"Loading SAM model ({self.model_type}) from {self.checkpoint_path}")
        
        self._sam = sam_model_registry[self.model_type](checkpoint=self.checkpoint_path)
        self._sam.to(device=self.device)
        
        self._mask_generator = SamAutomaticMaskGenerator(
            model=self._sam,
            points_per_side=self.points_per_side,
            pred_iou_thresh=self.pred_iou_thresh,
            stability_score_thresh=self.stability_score_thresh,
            min_mask_region_area=self.min_mask_region_area,
        )
        
        # Also create predictor for point-based mask generation
        self._predictor = SamPredictor(self._sam)
        
        logger.info("SAM model loaded successfully")
    
    def _refine_mask_by_color(
        self,
        image: np.ndarray,
        mask: np.ndarray,
        sample_points: List[tuple],
        color_tolerance: float = 30.0,
    ) -> np.ndarray:
        """
        Refine a mask by keeping only pixels with similar color to sample points,
        and only the connected region containing the center point.
        
        Args:
            image: RGB image (H, W, 3)
            mask: Binary mask to refine
            sample_points: List of (x, y) points to sample color from
            color_tolerance: Maximum color distance (in LAB space) to include
            
        Returns:
            Refined binary mask
        """
        from skimage import color as skcolor
        from scipy import ndimage
        
        height, width = image.shape[:2]
        
        # Convert image to LAB color space (better for perceptual color difference)
        image_lab = skcolor.rgb2lab(image)
        
        # Sample colors from the center region (inside drawn outline)
        sample_colors = []
        center_x, center_y = None, None
        for i, (x, y) in enumerate(sample_points):
            x, y = int(x), int(y)
            if 0 <= x < width and 0 <= y < height:
                sample_colors.append(image_lab[y, x])
                if i == 0:  # First point is center
                    center_x, center_y = x, y
        
        if len(sample_colors) == 0:
            return mask
        
        # Calculate mean color of sampled region
        mean_color = np.mean(sample_colors, axis=0)
        
        # For each pixel in the mask, check color distance
        color_mask = np.zeros_like(mask)
        
        # Get all mask pixel coordinates
        mask_ys, mask_xs = np.where(mask)
        
        for y, x in zip(mask_ys, mask_xs):
            pixel_lab = image_lab[y, x]
            # Euclidean distance in LAB space
            color_dist = np.sqrt(np.sum((pixel_lab - mean_color) ** 2))
            
            if color_dist <= color_tolerance:
                color_mask[y, x] = True
        
        # Keep only the connected component containing the center point
        # This removes disjoint areas with similar color
        if center_x is not None and center_y is not None:
            labeled_array, num_features = ndimage.label(color_mask)
            if num_features > 0 and color_mask[center_y, center_x]:
                center_label = labeled_array[center_y, center_x]
                refined_mask = (labeled_array == center_label)
            else:
                # Center not in mask, find largest component
                if num_features > 0:
                    component_sizes = ndimage.sum(color_mask, labeled_array, range(1, num_features + 1))
                    largest_label = np.argmax(component_sizes) + 1
                    refined_mask = (labeled_array == largest_label)
                else:
                    refined_mask = color_mask
        else:
            refined_mask = color_mask
        
        logger.debug(f"Color refinement: {np.sum(mask)} -> {np.sum(refined_mask)} pixels "
                    f"(tolerance={color_tolerance}, connected component)")
        
        return refined_mask
    
    def _smooth_mask_edges(
        self,
        mask: np.ndarray,
    ) -> np.ndarray:
        """
        Convert mask to a smooth polygon that contains all mask pixels.
        
        Creates a clean polygon boundary (not jagged pixels) that
        encompasses the entire color-determined mask area.
        
        The smoothing process:
        1. Applies Gaussian blur to soften jagged pixel edges
        2. Uses morphological operations to clean up the boundary
        3. Creates a smooth polygon contour using adaptive approximation
        4. Ensures all original mask pixels remain covered
        
        Args:
            mask: Binary mask
            
        Returns:
            Smoothed binary mask with clean polygon boundary
        """
        import cv2
        
        height, width = mask.shape
        image_scale = max(width, height) / 1000.0
        
        mask_uint8 = mask.astype(np.uint8) * 255
        original_area = np.sum(mask)
        
        # Step 1: Apply Gaussian blur to smooth jagged pixel edges
        blur_size = max(3, int(5 * image_scale))
        if blur_size % 2 == 0:
            blur_size += 1
        blurred = cv2.GaussianBlur(mask_uint8, (blur_size, blur_size), 0)
        
        # Re-threshold - use a lower threshold to ensure we don't lose edge pixels
        _, smoothed = cv2.threshold(blurred, 100, 255, cv2.THRESH_BINARY)
        
        # Step 2: Morphological closing to fill any small gaps
        kernel_size = max(3, int(5 * image_scale))
        if kernel_size % 2 == 0:
            kernel_size += 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        closed = cv2.morphologyEx(smoothed, cv2.MORPH_CLOSE, kernel)
        
        # Step 3: Find contours of the smoothed mask
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if len(contours) == 0:
            return mask
        
        # Get the largest contour
        largest_contour = max(contours, key=cv2.contourArea)
        
        # Step 4: Apply adaptive polygon approximation for smooth boundary
        # Use perimeter-based epsilon for consistent smoothing
        perimeter = cv2.arcLength(largest_contour, True)
        epsilon = max(1.0, perimeter * 0.003)  # 0.3% of perimeter - smooth but accurate
        smoothed_contour = cv2.approxPolyDP(largest_contour, epsilon, True)
        
        # Ensure we have enough points for a natural curve
        if len(smoothed_contour) < 8:
            epsilon = max(0.5, perimeter * 0.001)
            smoothed_contour = cv2.approxPolyDP(largest_contour, epsilon, True)
        
        # Create final mask from smoothed contour
        final_mask = np.zeros((height, width), dtype=np.uint8)
        cv2.fillPoly(final_mask, [smoothed_contour], 255)
        
        # Step 5: Ensure all original mask pixels are covered
        covered_pixels = np.sum((final_mask > 0) & mask)
        coverage = covered_pixels / original_area if original_area > 0 else 1.0
        
        if coverage < 0.98:  # Less than 98% coverage
            # Dilate the smoothed result to ensure full coverage
            small_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            dilated = cv2.dilate(final_mask, small_kernel, iterations=2)
            
            # Union with original to guarantee coverage
            combined = cv2.bitwise_or(dilated, mask_uint8)
            
            # Re-smooth the combined result
            combined_blur = cv2.GaussianBlur(combined, (blur_size, blur_size), 0)
            _, final_mask = cv2.threshold(combined_blur, 100, 255, cv2.THRESH_BINARY)
            
            logger.debug(f"Expanded boundary for full coverage (was {100*coverage:.0f}%)")
        
        logger.debug(f"Polygon smoothing: {original_area} -> {np.sum(final_mask > 0)} pixels")
        
        return final_mask > 0
    
    def generate_from_outline(
        self,
        image: np.ndarray,
        outline_points: List[tuple],  # List of (x, y) points from drawn outline
        color_tolerance: float = 6.0,  # Color tolerance in LAB space (lower = stricter)
    ) -> Optional[MaskData]:
        """
        Generate a mask from a drawn outline (circle/polygon).
        
        The outline provides hints to SAM, then the mask is refined by color:
        1. SAM generates candidate mask from outline hints
        2. Mask is clipped to only include pixels with similar color to the drawn area
        
        Args:
            image: Input image as numpy array (H, W, 3) in RGB format
            outline_points: List of (x, y) coordinates forming the drawn outline
            color_tolerance: Max color distance in LAB space (lower = stricter)
            
        Returns:
            MaskData object or None if generation fails
        """
        if len(outline_points) < 3:
            logger.warning("Need at least 3 points to form an outline")
            return None
        
        self._load_model()
        
        height, width = image.shape[:2]
        
        # Convert outline points to integers and clamp to image bounds
        xs = [int(max(0, min(width - 1, p[0]))) for p in outline_points]
        ys = [int(max(0, min(height - 1, p[1]))) for p in outline_points]
        
        # Calculate center point
        center_x = int(np.mean(xs))
        center_y = int(np.mean(ys))
        
        # Sample points along the outline (use every Nth point, max 15 points)
        num_points = min(15, len(outline_points))
        step = max(1, len(outline_points) // num_points)
        sampled_indices = list(range(0, len(outline_points), step))[:num_points]
        
        # Create point prompts: center + sampled outline points
        # All labeled as foreground (1)
        input_points = [[center_x, center_y]]
        input_labels = [1]  # Center is foreground
        
        for i in sampled_indices:
            input_points.append([xs[i], ys[i]])
            input_labels.append(1)  # Outline points are foreground
        
        input_points = np.array(input_points)
        input_labels = np.array(input_labels)
        
        # Set image for predictor
        self._predictor.set_image(image)
        
        # Strategy 1: Try with just points (no box) - let SAM find natural boundaries
        masks_no_box, scores_no_box, _ = self._predictor.predict(
            point_coords=input_points,
            point_labels=input_labels,
            multimask_output=True,
        )
        
        # Strategy 2: Try with bounding box (small padding - outline is the boundary hint)
        box_width = max(xs) - min(xs)
        box_height = max(ys) - min(ys)
        padding_x = max(10, int(box_width * 0.15))  # Small padding - 15% or 10px min
        padding_y = max(10, int(box_height * 0.15))  # Small padding - 15% or 10px min
        
        box_x0 = max(0, min(xs) - padding_x)
        box_y0 = max(0, min(ys) - padding_y)
        box_x1 = min(width, max(xs) + padding_x)
        box_y1 = min(height, max(ys) + padding_y)
        box = np.array([box_x0, box_y0, box_x1, box_y1])
        
        masks_with_box, scores_with_box, _ = self._predictor.predict(
            point_coords=input_points,
            point_labels=input_labels,
            box=box,
            multimask_output=True,
        )
        
        # Combine all masks and pick the best one
        all_masks = list(masks_no_box) + list(masks_with_box)
        all_scores = list(scores_no_box) + list(scores_with_box)
        
        if len(all_masks) == 0:
            return None
        
        # Calculate the area of the drawn outline (approximate)
        outline_area = box_width * box_height
        
        # Score masks: prefer ones that closely match the drawn outline
        # The outline represents the BOUNDARY the user wants, not interior points
        best_idx = None
        best_combined_score = -1
        
        for i, (mask, sam_score) in enumerate(zip(all_masks, all_scores)):
            mask_area = np.sum(mask)
            
            # 1. Coverage: outline points should be inside the mask
            points_inside = sum(1 for px, py in zip(xs, ys) if mask[py, px])
            coverage = points_inside / len(xs) if len(xs) > 0 else 0
            
            # 2. Size match: penalize masks much larger than the drawn outline
            # We want the mask to be close to the size of what was drawn
            size_ratio = mask_area / outline_area if outline_area > 0 else 1.0
            if size_ratio <= 1.5:
                # Mask is same size or smaller - good
                size_score = 1.0
            elif size_ratio <= 2.0:
                # Mask is up to 2x larger - slight penalty
                size_score = 0.8
            elif size_ratio <= 3.0:
                # Mask is up to 3x larger - moderate penalty
                size_score = 0.5
            else:
                # Mask is much larger than drawn - heavy penalty
                size_score = 0.2
            
            # 3. Boundary alignment: check if outline points are near the mask edge
            # For each outline point inside the mask, check if it's close to a non-mask pixel
            edge_distance = 8  # pixels
            points_near_edge = 0
            for px, py in zip(xs, ys):
                if not mask[py, px]:
                    continue
                # Check if any pixel within edge_distance is outside the mask
                near_edge = False
                for dy in range(-edge_distance, edge_distance + 1):
                    for dx in range(-edge_distance, edge_distance + 1):
                        ny, nx = py + dy, px + dx
                        if 0 <= ny < height and 0 <= nx < width:
                            if not mask[ny, nx]:
                                near_edge = True
                                break
                    if near_edge:
                        break
                if near_edge:
                    points_near_edge += 1
            
            edge_ratio = points_near_edge / max(1, points_inside) if points_inside > 0 else 0
            
            # Combined score: coverage + size match + boundary alignment
            # Weight: 30% SAM score, 25% coverage, 25% size match, 20% boundary alignment
            combined = (0.30 * float(sam_score) + 
                       0.25 * coverage + 
                       0.25 * size_score + 
                       0.20 * edge_ratio)
            
            logger.debug(f"Mask {i}: sam={sam_score:.2f}, coverage={coverage:.2f}, "
                        f"size_ratio={size_ratio:.1f}, size_score={size_score:.2f}, "
                        f"edge_ratio={edge_ratio:.2f}, combined={combined:.3f}")
            
            if combined > best_combined_score:
                best_combined_score = combined
                best_idx = i
        
        mask = all_masks[best_idx]
        score = float(all_scores[best_idx])
        
        # CRITICAL: Refine mask by color - only keep pixels with similar color to drawn area
        # Sample colors from inside the drawn outline (center + some outline points)
        sample_points = [(center_x, center_y)]
        # Add some points from inside the outline (not on the edge)
        for i in range(0, len(xs), max(1, len(xs) // 5)):
            # Move points slightly toward center
            px = int(xs[i] * 0.7 + center_x * 0.3)
            py = int(ys[i] * 0.7 + center_y * 0.3)
            sample_points.append((px, py))
        
        original_area = np.sum(mask)
        mask = self._refine_mask_by_color(image, mask, sample_points, color_tolerance)
        refined_area = np.sum(mask)
        
        logger.info(f"Color refinement: {original_area} -> {refined_area} pixels "
                   f"({100*refined_area/original_area:.0f}% retained)")
        
        # Smooth edges to remove jagged pixel boundaries (auto-scales to image size)
        mask = self._smooth_mask_edges(mask)
        smoothed_area = np.sum(mask)
        
        logger.info(f"Edge smoothing: {refined_area} -> {smoothed_area} pixels")
        
        # Convert to MaskData
        mask_area = int(np.sum(mask))
        if mask_area < self.min_mask_region_area:
            logger.debug(f"Generated mask too small after color refinement ({mask_area} < {self.min_mask_region_area})")
            return None
        
        # Calculate bounding box
        y_coords, x_coords = np.where(mask)
        if len(y_coords) == 0:
            return None
        
        bbox = (
            int(x_coords.min()),
            int(y_coords.min()),
            int(x_coords.max() - x_coords.min()),
            int(y_coords.max() - y_coords.min()),
        )
        
        mask_data = MaskData(
            id=f"outline_mask_{center_x}_{center_y}",
            mask=mask,
            area=mask_area,
            bbox=bbox,
            predicted_iou=score,
            stability_score=score,
        )
        
        # Calculate outline coverage for logging
        points_inside = sum(1 for px, py in zip(xs, ys) if mask[py, px])
        coverage = points_inside / len(xs) if len(xs) > 0 else 0
        
        logger.info(f"Generated mask from outline: area={mask_area}, score={score:.3f}, "
                   f"coverage={coverage:.1%}, center=({center_x},{center_y}), "
                   f"outline_bounds=({min(xs)},{min(ys)})-({max(xs)},{max(ys)})")
        return mask_data
    
    def generate_filled_polygon(
        self,
        image: np.ndarray,
        outline_points: List[tuple],  # List of (x, y) points from drawn outline
        smooth_edges: bool = True,
    ) -> Optional[MaskData]:
        """
        Generate a completely filled mask from a drawn polygon (no SAM, no color filtering).
        
        This is useful when SAM's color-based refinement misses parts of an area
        due to inconsistent shading. The user can draw a polygon that will be
        completely filled without any SAM processing.
        
        Args:
            image: Input image as numpy array (H, W, 3) in RGB format (used for dimensions)
            outline_points: List of (x, y) coordinates forming the drawn polygon
            smooth_edges: If True, applies edge smoothing to the polygon
            
        Returns:
            MaskData object or None if generation fails
        """
        import cv2
        
        if len(outline_points) < 3:
            logger.warning("Need at least 3 points to form a polygon")
            return None
        
        height, width = image.shape[:2]
        image_scale = max(width, height) / 1000.0
        
        # Convert outline points to integers and clamp to image bounds
        xs = [int(max(0, min(width - 1, p[0]))) for p in outline_points]
        ys = [int(max(0, min(height - 1, p[1]))) for p in outline_points]
        
        # Calculate center point
        center_x = int(np.mean(xs))
        center_y = int(np.mean(ys))
        
        # Step 1: Smooth the input polygon points before filling
        # This reduces jaggedness from hand-drawn input
        if smooth_edges and len(outline_points) > 10:
            # Convert to contour format for approxPolyDP
            contour = np.array([[x, y] for x, y in zip(xs, ys)], dtype=np.float32)
            
            # Calculate perimeter and use adaptive epsilon
            perimeter = cv2.arcLength(contour, True)
            epsilon = max(1.0, perimeter * 0.01)  # 1% of perimeter
            smoothed_contour = cv2.approxPolyDP(contour, epsilon, True)
            
            # Update xs, ys with smoothed points
            xs = [int(p[0][0]) for p in smoothed_contour]
            ys = [int(p[0][1]) for p in smoothed_contour]
        
        # Step 2: Create polygon mask by filling the (smoothed) outline
        mask = np.zeros((height, width), dtype=np.uint8)
        polygon_points = np.array([[x, y] for x, y in zip(xs, ys)], dtype=np.int32)
        cv2.fillPoly(mask, [polygon_points], 255)
        
        original_area = np.sum(mask > 0)
        
        # Step 3: Apply additional smoothing to remove pixel-level jaggedness
        # Skip smoothing for small polygons to avoid eliminating them
        if smooth_edges and original_area > 500:
            # Gaussian blur to soften edges
            blur_size = max(3, int(5 * image_scale))
            if blur_size % 2 == 0:
                blur_size += 1
            blurred = cv2.GaussianBlur(mask, (blur_size, blur_size), 0)
            _, smoothed = cv2.threshold(blurred, 127, 255, cv2.THRESH_BINARY)
            
            # Find contours and simplify
            contours, _ = cv2.findContours(smoothed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if len(contours) > 0:
                largest_contour = max(contours, key=cv2.contourArea)
                
                # Apply polygon approximation for final smooth boundary
                perimeter = cv2.arcLength(largest_contour, True)
                epsilon = max(1.0, perimeter * 0.005)  # 0.5% of perimeter
                final_contour = cv2.approxPolyDP(largest_contour, epsilon, True)
                
                # Create final mask
                mask = np.zeros((height, width), dtype=np.uint8)
                cv2.fillPoly(mask, [final_contour], 255)
        elif smooth_edges and original_area <= 500:
            logger.info(f"Skipping smoothing for small polygon ({original_area} pixels)")
        
        # Convert to boolean mask
        mask = mask > 0
        smoothed_area = np.sum(mask)
        
        logger.info(f"Filled polygon: {original_area} -> {smoothed_area} pixels")
        
        # Calculate mask area
        mask_area = int(np.sum(mask))
        # Use lower threshold for user-drawn polygons (allow smaller areas)
        min_area = min(50, self.min_mask_region_area)  # At least 50 pixels for fill
        if mask_area < min_area:
            logger.warning(f"Generated filled polygon too small ({mask_area} < {min_area})")
            print(f"[FILL] Polygon too small: {mask_area} pixels (need at least {min_area})")
            return None
        
        # Calculate bounding box
        y_coords, x_coords = np.where(mask)
        if len(y_coords) == 0:
            return None
        
        bbox = (
            int(x_coords.min()),
            int(y_coords.min()),
            int(x_coords.max() - x_coords.min()),
            int(y_coords.max() - y_coords.min()),
        )
        
        mask_data = MaskData(
            id=f"filled_polygon_{center_x}_{center_y}",
            mask=mask,
            area=mask_area,
            bbox=bbox,
            predicted_iou=1.0,  # User-defined polygon, assume perfect
            stability_score=1.0,
        )
        
        logger.info(f"Generated filled polygon mask: area={mask_area}, "
                   f"center=({center_x},{center_y}), "
                   f"bounds=({min(xs)},{min(ys)})-({max(xs)},{max(ys)})")
        return mask_data

    def generate_from_point(
        self,
        image: np.ndarray,
        point: tuple,  # (x, y) in image coordinates
        label: int = 1,  # 1 = foreground point, 0 = background point
        box_size: Optional[int] = None,  # Optional bounding box size to constrain search
    ) -> Optional[MaskData]:
        """
        Generate a mask from a single point prompt.
        
        For better results, consider using generate_from_outline() which allows
        drawing an outline to provide SAM with more context.
        
        Args:
            image: Input image as numpy array (H, W, 3) in RGB format
            point: Point coordinates (x, y) in image space
            label: Point label (1 = foreground, 0 = background)
            box_size: Optional bounding box size (pixels) to constrain initial search area.
            
        Returns:
            MaskData object or None if generation fails
        """
        self._load_model()
        
        x, y = point
        height, width = image.shape[:2]
        
        # Validate point
        if x < 0 or x >= width or y < 0 or y >= height:
            logger.warning(f"Point ({x}, {y}) is outside image bounds ({width}, {height})")
            return None
        
        # Set image for predictor
        self._predictor.set_image(image)
        
        # Generate mask from point
        input_point = np.array([[x, y]])
        input_label = np.array([label])
        
        # Simple approach: just use the point without box constraint
        # Let SAM decide the best segmentation
        masks, scores, logits = self._predictor.predict(
            point_coords=input_point,
            point_labels=input_label,
            multimask_output=True,
        )
        
        if len(masks) == 0:
            return None
        
        # Select mask where the click point is inside and has highest score
        best_idx = None
        best_score = -1
        
        for i, (mask, score) in enumerate(zip(masks, scores)):
            # Check if click point is inside this mask
            if mask[int(y), int(x)]:
                if score > best_score:
                    best_score = score
                    best_idx = i
        
        # If no mask contains the point, fall back to highest score
        if best_idx is None:
            best_idx = np.argmax(scores)
        
        mask = masks[best_idx]
        score = float(scores[best_idx])
        
        logger.debug(f"Selected mask {best_idx}: score={score:.3f}")
        
        # Convert to MaskData
        mask_area = int(np.sum(mask))
        if mask_area < self.min_mask_region_area:
            logger.debug(f"Generated mask too small ({mask_area} < {self.min_mask_region_area})")
            return None
        
        # Calculate bounding box
        y_coords, x_coords = np.where(mask)
        if len(y_coords) == 0:
            return None
        
        bbox = (
            int(x_coords.min()),
            int(y_coords.min()),
            int(x_coords.max() - x_coords.min()),
            int(y_coords.max() - y_coords.min()),
        )
        
        mask_data = MaskData(
            id=f"point_mask_{x}_{y}",
            mask=mask,
            area=mask_area,
            bbox=bbox,
            predicted_iou=score,
            stability_score=score,
        )
        
        logger.debug(f"Generated mask from point ({x}, {y}): area={mask_area}, score={score:.3f}")
        return mask_data
    
    def generate_from_box(
        self,
        image: np.ndarray,
        box: tuple,  # (x1, y1, x2, y2)
    ) -> Optional[MaskData]:
        """
        Generate a mask from a bounding box prompt.
        
        Args:
            image: Input image as numpy array (H, W, 3) in RGB format
            box: Bounding box (x1, y1, x2, y2)
            
        Returns:
            MaskData object or None if generation fails
        """
        self._load_model()
        
        # Set image for predictor
        self._predictor.set_image(image)
        
        # Convert box to numpy array
        input_box = np.array(box)
        
        # Generate mask from box
        masks, scores, logits = self._predictor.predict(
            point_coords=None,
            point_labels=None,
            box=input_box[None, :],
            multimask_output=True,
        )
        
        if len(masks) == 0:
            return None
        
        # Select mask with highest score
        best_idx = np.argmax(scores)
        mask = masks[best_idx]
        score = float(scores[best_idx])
        
        # Convert to MaskData
        mask_area = int(np.sum(mask))
        if mask_area < self.min_mask_region_area:
            logger.debug(f"Generated mask too small ({mask_area} < {self.min_mask_region_area})")
            return None
        
        # Calculate bounding box
        y_coords, x_coords = np.where(mask)
        if len(y_coords) == 0:
            return None
            
        bbox = (
            int(x_coords.min()),
            int(y_coords.min()),
            int(x_coords.max() - x_coords.min()),
            int(y_coords.max() - y_coords.min()),
        )
        
        mask_data = MaskData(
            id=f"box_mask_{box[0]}_{box[1]}",
            mask=mask,
            area=mask_area,
            bbox=bbox,
            predicted_iou=score,
            stability_score=score,
        )
        
        return mask_data

    def generate(self, image: np.ndarray) -> List[MaskData]:
        """
        Generate masks from an image.
        
        Args:
            image: Input image as numpy array (H, W, 3) in RGB format
            
        Returns:
            List of MaskData objects containing masks and metadata
        """
        self._load_model()
        
        logger.info(f"Generating masks for image of shape {image.shape}")
        
        # Run SAM automatic mask generation
        sam_masks = self._mask_generator.generate(image)
        
        logger.info(f"Generated {len(sam_masks)} candidate masks")
        
        # Convert to MaskData objects
        masks = []
        for i, sam_mask in enumerate(sam_masks):
            mask_data = MaskData(
                id=f"mask_{i:04d}",
                mask=sam_mask["segmentation"],
                area=sam_mask["area"],
                bbox=tuple(sam_mask["bbox"]),
                predicted_iou=sam_mask["predicted_iou"],
                stability_score=sam_mask["stability_score"],
            )
            masks.append(mask_data)
        
        return masks
    
    def generate_from_file(self, image_path: Path) -> List[MaskData]:
        """
        Generate masks from an image file.
        
        Args:
            image_path: Path to input image
            
        Returns:
            List of MaskData objects
        """
        logger.info(f"Loading image from {image_path}")
        image = np.array(Image.open(image_path).convert("RGB"))
        return self.generate(image)
    
    def save_masks(
        self,
        masks: List[MaskData],
        output_dir: Path,
    ) -> None:
        """
        Save masks to disk.
        
        Args:
            masks: List of MaskData objects
            output_dir: Directory to save masks
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for mask_data in masks:
            # Save mask as PNG
            mask_path = output_dir / f"{mask_data.id}.png"
            mask_img = Image.fromarray((mask_data.mask * 255).astype(np.uint8))
            mask_img.save(mask_path)
            
            # Save metadata as JSON
            meta_path = output_dir / f"{mask_data.id}.json"
            with open(meta_path, "w") as f:
                json.dump(mask_data.to_dict(), f, indent=2)
        
        logger.info(f"Saved {len(masks)} masks to {output_dir}")
    
    @staticmethod
    def load_masks(masks_dir: Path) -> List[MaskData]:
        """
        Load masks from disk.
        
        Args:
            masks_dir: Directory containing saved masks
            
        Returns:
            List of MaskData objects
        """
        masks_dir = Path(masks_dir)
        masks = []
        
        for meta_path in sorted(masks_dir.glob("*.json")):
            with open(meta_path) as f:
                meta = json.load(f)
            
            mask_path = masks_dir / f"{meta['id']}.png"
            mask_img = Image.open(mask_path)
            mask = np.array(mask_img) > 127
            
            mask_data = MaskData(
                id=meta["id"],
                mask=mask,
                area=meta["area"],
                bbox=tuple(meta["bbox"]),
                predicted_iou=meta["predicted_iou"],
                stability_score=meta["stability_score"],
            )
            masks.append(mask_data)
        
        logger.info(f"Loaded {len(masks)} masks from {masks_dir}")
        return masks


def merge_masks(
    masks: List[MaskData],
    smooth_edges: bool = True,
    new_id: Optional[str] = None,
) -> Optional[MaskData]:
    """
    Merge multiple masks into a single mask with smooth edges.
    
    This is useful when a SAM-generated mask doesn't fully cover an area
    and you want to combine it with a manually-drawn filled polygon.
    The result is a single mask with smooth, clean boundaries.
    
    The smoothing algorithm:
    1. Combines all masks with OR operation
    2. Applies Gaussian blur to soften harsh boundaries
    3. Uses morphological closing to fill gaps between masks
    4. Applies multiple smoothing passes to eliminate jagged edges
    5. Creates a clean polygon contour that encompasses all original pixels
    
    Args:
        masks: List of MaskData objects to merge
        smooth_edges: If True, applies edge smoothing to the merged result
        new_id: Optional custom ID for the merged mask
        
    Returns:
        Merged MaskData object or None if no masks provided
    """
    import cv2
    from scipy import ndimage
    
    if not masks:
        logger.warning("No masks provided for merging")
        return None
    
    if len(masks) == 1:
        logger.info("Only one mask provided, returning as-is")
        return masks[0]
    
    # Get image dimensions from first mask
    first_mask = masks[0].mask
    height, width = first_mask.shape
    
    # Create combined mask by OR-ing all masks together
    combined_mask = np.zeros((height, width), dtype=bool)
    for mask_data in masks:
        combined_mask = combined_mask | mask_data.mask
    
    original_area = np.sum(combined_mask)
    logger.info(f"Combined {len(masks)} masks: total area = {original_area} pixels")
    
    if smooth_edges:
        # Convert to uint8 for OpenCV operations
        mask_uint8 = combined_mask.astype(np.uint8) * 255
        
        # Calculate scale factor for kernel sizes
        image_scale = max(width, height) / 1000.0
        
        # Step 1: Apply Gaussian blur to soften harsh mask boundaries
        # This helps blend the SAM mask edge with the filled polygon edge
        blur_size = max(5, int(9 * image_scale))
        if blur_size % 2 == 0:
            blur_size += 1
        blurred = cv2.GaussianBlur(mask_uint8, (blur_size, blur_size), 0)
        
        # Re-threshold after blur (this smooths the boundary)
        _, smoothed = cv2.threshold(blurred, 127, 255, cv2.THRESH_BINARY)
        
        # Step 2: Morphological closing to fill gaps between merged masks
        # Use elliptical kernel for more natural curves
        close_kernel_size = max(5, int(11 * image_scale))
        if close_kernel_size % 2 == 0:
            close_kernel_size += 1
        close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (close_kernel_size, close_kernel_size))
        closed = cv2.morphologyEx(smoothed, cv2.MORPH_CLOSE, close_kernel)
        
        # Step 3: Ensure we don't lose any original pixels - dilate slightly
        # then intersect with closed result
        small_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        original_dilated = cv2.dilate(mask_uint8, small_kernel, iterations=2)
        
        # Combine: keep original area + smoothed boundary
        combined_smoothed = cv2.bitwise_or(closed, original_dilated)
        
        # Step 4: Apply another blur + threshold for final smoothing
        final_blur_size = max(3, int(7 * image_scale))
        if final_blur_size % 2 == 0:
            final_blur_size += 1
        final_blurred = cv2.GaussianBlur(combined_smoothed, (final_blur_size, final_blur_size), 0)
        _, final_smoothed = cv2.threshold(final_blurred, 127, 255, cv2.THRESH_BINARY)
        
        # Step 5: Find contours and create smooth polygon boundary
        contours, _ = cv2.findContours(final_smoothed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if len(contours) > 0:
            # Get the largest contour
            largest_contour = max(contours, key=cv2.contourArea)
            
            # Apply contour smoothing using approxPolyDP with adaptive epsilon
            # Smaller epsilon = more accurate but potentially jaggier
            # We want smooth but not lose too much detail
            perimeter = cv2.arcLength(largest_contour, True)
            epsilon = max(1.0, perimeter * 0.005)  # 0.5% of perimeter
            smoothed_contour = cv2.approxPolyDP(largest_contour, epsilon, True)
            
            # If the contour is too simplified, use a smaller epsilon
            if len(smoothed_contour) < 10:
                epsilon = max(0.5, perimeter * 0.002)
                smoothed_contour = cv2.approxPolyDP(largest_contour, epsilon, True)
            
            # Create final mask from smoothed contour
            final_mask = np.zeros((height, width), dtype=np.uint8)
            cv2.fillPoly(final_mask, [smoothed_contour], 255)
            
            # CRITICAL: Ensure all original mask pixels are covered
            # The smoothed boundary must contain the original area
            covered_pixels = np.sum((final_mask > 0) & combined_mask)
            coverage_ratio = covered_pixels / original_area if original_area > 0 else 1.0
            
            if coverage_ratio < 0.98:  # Less than 98% coverage
                logger.debug(f"Coverage only {100*coverage_ratio:.0f}%, expanding boundary...")
                
                # Dilate the smoothed contour to ensure full coverage
                dilated_final = cv2.dilate(final_mask, small_kernel, iterations=2)
                
                # Blend: union of dilated smooth mask with original
                expanded = cv2.bitwise_or(dilated_final, mask_uint8)
                
                # Re-smooth the expanded mask
                expanded_blur = cv2.GaussianBlur(expanded, (final_blur_size, final_blur_size), 0)
                _, expanded_smooth = cv2.threshold(expanded_blur, 100, 255, cv2.THRESH_BINARY)
                
                final_mask = expanded_smooth
            
            combined_mask = final_mask > 0
        
        smoothed_area = np.sum(combined_mask)
        logger.info(f"Edge smoothing: {original_area} -> {smoothed_area} pixels "
                   f"({100*smoothed_area/original_area:.0f}% of original)")
    
    # Calculate final area
    mask_area = int(np.sum(combined_mask))
    if mask_area == 0:
        logger.warning("Merged mask is empty")
        return None
    
    # Calculate bounding box
    y_coords, x_coords = np.where(combined_mask)
    bbox = (
        int(x_coords.min()),
        int(y_coords.min()),
        int(x_coords.max() - x_coords.min()),
        int(y_coords.max() - y_coords.min()),
    )
    
    # Calculate centroid
    center_x = int(np.mean(x_coords))
    center_y = int(np.mean(y_coords))
    
    # Generate ID if not provided
    if new_id is None:
        mask_ids = "_".join(m.id.split("_")[-1] for m in masks[:3])
        new_id = f"merged_{mask_ids}_{center_x}_{center_y}"
    
    # Calculate average scores from merged masks
    avg_iou = np.mean([m.predicted_iou for m in masks])
    avg_stability = np.mean([m.stability_score for m in masks])
    
    merged_mask_data = MaskData(
        id=new_id,
        mask=combined_mask,
        area=mask_area,
        bbox=bbox,
        predicted_iou=avg_iou,
        stability_score=avg_stability,
    )
    
    logger.info(f"Merged {len(masks)} masks into '{new_id}': area={mask_area}, center=({center_x},{center_y})")
    return merged_mask_data


# Standalone function for simple usage
def generate_masks(
    image_path: Path,
    output_dir: Path,
    checkpoint_path: str,
    **kwargs: Any,
) -> List[MaskData]:
    """
    Convenience function to generate and save masks.
    
    Args:
        image_path: Path to input image
        output_dir: Directory to save masks
        checkpoint_path: Path to SAM checkpoint
        **kwargs: Additional arguments for MaskGenerator
        
    Returns:
        List of MaskData objects
    """
    generator = MaskGenerator(checkpoint_path=checkpoint_path, **kwargs)
    masks = generator.generate_from_file(image_path)
    generator.save_masks(masks, output_dir)
    return masks
