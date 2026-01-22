"""
Visualization utilities for interactive selection.

Provides functions to visualize masks overlaid on images for user interaction.
"""

import numpy as np
from typing import List, Tuple, Optional, Dict, Callable
from pathlib import Path
import logging

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    from matplotlib.widgets import Button
    from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    try:
        from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk as NavigationToolbar
    except ImportError:
        NavigationToolbar = None
    MATPLOTLIB_AVAILABLE = False

from .masks import MaskData
from .interactive import InteractiveSelector, FeatureType
from .svg import SVGGenerator

logger = logging.getLogger(__name__)

# Cache OPCD palette to avoid reloading on every redraw
_OPCD_PALETTE_CACHE = None
_OPCD_RGB_CACHE = None

def _get_opcd_colors():
    """Get OPCD colors, cached after first load."""
    global _OPCD_PALETTE_CACHE, _OPCD_RGB_CACHE
    
    if _OPCD_PALETTE_CACHE is None:
        _OPCD_PALETTE_CACHE = SVGGenerator.load_opcd_palette()
        # Pre-convert hex to RGB arrays for performance
        _OPCD_RGB_CACHE = {}
        for key, hex_color in _OPCD_PALETTE_CACHE.items():
            hex_color = hex_color.lstrip('#')
            _OPCD_RGB_CACHE[key] = np.array([int(hex_color[i:i+2], 16) for i in (0, 2, 4)])
    
    return _OPCD_PALETTE_CACHE, _OPCD_RGB_CACHE


def create_mask_overlay(
    image: np.ndarray,
    masks: List[MaskData],
    selected_mask_ids: Optional[List[str]] = None,
    alpha: float = 0.5,
) -> np.ndarray:
    """
    Create an overlay visualization showing masks on the image.
    Uses OPCD palette colors based on feature type.
    
    Args:
        image: Source image (H, W, 3) in RGB
        masks: List of masks to display
        selected_mask_ids: Optional list of selected mask IDs to highlight
        alpha: Transparency for mask overlay
        
    Returns:
        Overlaid image
    """
    overlay = image.copy().astype(float)
    
    selected_ids = set(selected_mask_ids or [])
    
    # Get cached OPCD palette colors (only loaded once)
    opcd_colors, opcd_rgb = _get_opcd_colors()
    
    # Default colors if feature type can't be determined
    default_color = opcd_rgb.get('ignore', np.array([204, 204, 204]))
    selected_highlight = np.array([255, 0, 0])  # Red border for selected
    
    for mask_data in masks:
        mask = mask_data.mask
        is_selected = mask_data.id in selected_ids
        
        # Determine feature type from mask ID
        # Format: "green_1_0000", "fairway_2_0001", "bunker_1_0002", etc.
        mask_id_lower = mask_data.id.lower()
        feature_color = default_color
        
        if 'green' in mask_id_lower:
            feature_color = opcd_rgb.get('green', np.array([188, 229, 164]))
        elif 'fairway' in mask_id_lower:
            feature_color = opcd_rgb.get('fairway', np.array([67, 229, 97]))
        elif 'bunker' in mask_id_lower:
            feature_color = opcd_rgb.get('bunker', np.array([229, 229, 170]))
        elif 'tee' in mask_id_lower:
            feature_color = opcd_rgb.get('tee', np.array([160, 229, 184]))
        elif 'rough' in mask_id_lower:
            feature_color = opcd_rgb.get('rough', np.array([39, 132, 56]))
        elif 'water' in mask_id_lower or 'lake' in mask_id_lower:
            feature_color = opcd_rgb.get('water', np.array([0, 0, 192]))
        elif 'cart_path' in mask_id_lower or 'concrete' in mask_id_lower:
            feature_color = opcd_rgb.get('cart_path', np.array([190, 190, 187]))
        
        # Use feature color, but make selected masks more visible
        if is_selected:
            # Blend feature color with red highlight for selected
            color = (feature_color * 0.7 + selected_highlight * 0.3).astype(int)
            mask_alpha = alpha * 0.8  # More opaque for selected
        else:
            color = feature_color
            mask_alpha = alpha * 0.4  # Less opaque for unselected
        
        # Apply mask overlay
        for c in range(3):
            overlay[:, :, c][mask] = (
                overlay[:, :, c][mask] * (1 - mask_alpha) +
                color[c] * mask_alpha
            )
    
    return overlay.astype(np.uint8)


class InteractiveMaskSelector:
    """
    Interactive matplotlib-based mask selector with click-to-select functionality.
    Supports buttons and keyboard shortcuts for smoother workflow.
    
    Drawing Modes:
    - SAM mode (default): Draw outline, SAM generates mask with color refinement
    - Fill mode ('F' key): Draw polygon that gets completely filled (no SAM processing)
    
    Additional Features:
    - Merge ('M' key): Merge all selected masks into one with smooth edges
    """
    
    def __init__(
        self,
        selector: InteractiveSelector,
        title: str = "Click on masks to select",
    ):
        """
        Initialize interactive selector.
        
        Args:
            selector: InteractiveSelector instance
            title: Window title
        """
        if not MATPLOTLIB_AVAILABLE:
            raise ImportError("matplotlib is required for interactive visualization")
        
        self.selector = selector
        self.title = title
        self.selected_mask_ids: List[str] = []
        self.click_callback: Optional[Callable[[str], None]] = None
        self.done_callback: Optional[Callable[[], None]] = None
        self.fig = None
        self.ax = None
        self.done_button = None
        self._done_pressed = False
        self._image_artist = None  # Cache image artist for efficient updates
        self._last_generated_mask_id = None  # Track last generated mask for undo
        
        # Drawing mode state
        self._drawing = False
        self._draw_points = []  # Points collected during drawing
        self._draw_line = None  # Line artist for drawing visualization
        
        # Fill mode: if True, draws are filled polygons (no SAM), else SAM outline mode
        self._fill_mode = False
        self._mode_text = None  # Text artist showing current mode
        
    def _setup_instructions_panel(self):
        """Setup the left instructions panel with controls and shortcuts."""
        ax = self.ax_instructions
        
        # Title
        ax.text(0.5, 0.97, "Controls", fontsize=14, fontweight='bold',
                ha='center', va='top', transform=ax.transAxes)
        
        # Instructions text
        instructions = [
            "",
            "DRAWING:",
            "  Click+drag to outline",
            "  a feature area",
            "",
            "KEYBOARD:",
            "  F = Toggle Fill mode",
            "      SAM: analyzes color",
            "      FILL: exact polygon",
            "",
            "  M = Merge masks",
            "",
            "  Esc = Undo last",
            "",
            "  Enter/Space = Done",
            "",
            "MOUSE:",
            "  Scroll = Zoom in/out",
            "  Drag = Pan (toolbar)",
            "",
            "─" * 15,
        ]
        
        y_pos = 0.90
        for line in instructions:
            ax.text(0.05, y_pos, line, fontsize=9, fontfamily='monospace',
                    ha='left', va='top', transform=ax.transAxes)
            y_pos -= 0.04
        
        # Mode indicator (will be updated in _update_instructions)
        self._mode_label = ax.text(0.5, 0.22, "Mode: SAM", fontsize=12, fontweight='bold',
                                   ha='center', va='top', transform=ax.transAxes,
                                   bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.9))
        
        # Selected count
        self._selected_label = ax.text(0.5, 0.14, "Selected: 0", fontsize=11,
                                       ha='center', va='top', transform=ax.transAxes,
                                       bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.7))
        
        # Current task hint
        self._task_label = ax.text(0.5, 0.06, "", fontsize=9, style='italic',
                                   ha='center', va='top', transform=ax.transAxes,
                                   wrap=True)
    
    def _update_instructions(self):
        """Update the dynamic parts of the instructions panel."""
        if not hasattr(self, '_mode_label'):
            return
        
        # Update mode
        mode_name = "FILL" if self._fill_mode else "SAM"
        mode_color = 'orange' if self._fill_mode else 'lightblue'
        self._mode_label.set_text(f"Mode: {mode_name}")
        self._mode_label.set_bbox(dict(boxstyle='round', facecolor=mode_color, alpha=0.9))
        
        # Update selected count
        self._selected_label.set_text(f"Selected: {len(self.selected_mask_ids)}")
        
        # Update task hint based on context
        if hasattr(self, '_current_feature_type') and hasattr(self, '_current_hole'):
            feature_name = self._current_feature_type.value if self._current_feature_type else "feature"
            self._task_label.set_text(f"Draw {feature_name} for hole {self._current_hole}")

    def _is_toolbar_active(self):
        """Check if pan or zoom tool is active in the toolbar."""
        try:
            toolbar = self.fig.canvas.toolbar
            if toolbar is not None:
                # Check for pan or zoom mode
                mode = getattr(toolbar, 'mode', '')
                if mode in ('pan/zoom', 'pan', 'zoom', 'zoom rect'):
                    return True
                # Also check _active for some backends
                active = getattr(toolbar, '_active', None)
                if active in ('PAN', 'ZOOM'):
                    return True
        except:
            pass
        return False
    
    def _on_press(self, event):
        """Handle mouse button press - start drawing."""
        # Don't draw if pan/zoom tool is active
        if self._is_toolbar_active():
            return
        
        if hasattr(event, 'inaxes') and event.inaxes != self.ax:
            return
        
        if event.button != 1:  # Only left mouse button
            return
        
        if event.xdata is None or event.ydata is None:
            return
        
        # Start drawing
        self._drawing = True
        self._draw_points = [(event.xdata, event.ydata)]
        
        # Create line artist for drawing visualization
        if self._draw_line is not None:
            self._draw_line.remove()
        self._draw_line, = self.ax.plot([], [], 'r-', linewidth=2, alpha=0.7)
        
    def _on_motion(self, event):
        """Handle mouse motion - collect drawing points."""
        if not self._drawing:
            return
        
        # Cancel drawing if toolbar became active
        if self._is_toolbar_active():
            self._drawing = False
            if self._draw_line is not None:
                self._draw_line.remove()
                self._draw_line = None
            self._draw_points = []
            return
        
        if event.xdata is None or event.ydata is None:
            return
        
        if event.inaxes != self.ax:
            return
        
        # Add point to drawing
        self._draw_points.append((event.xdata, event.ydata))
        
        # Update line visualization
        if self._draw_line is not None and len(self._draw_points) > 1:
            xs = [p[0] for p in self._draw_points]
            ys = [p[1] for p in self._draw_points]
            self._draw_line.set_data(xs, ys)
            self.fig.canvas.draw_idle()
    
    def _on_release(self, event):
        """Handle mouse button release - finish drawing and generate mask."""
        if not self._drawing:
            return
        
        self._drawing = False
        
        # Need at least a few points to form an outline
        if len(self._draw_points) < 5:
            logger.info("Draw a larger outline (click and drag)")
            if self._draw_line is not None:
                self._draw_line.remove()
                self._draw_line = None
            self.fig.canvas.draw_idle()
            return
        
        # Process events before heavy SAM work to keep GUI responsive
        try:
            self.fig.canvas.flush_events()
        except:
            pass
        
        # Check if this is a point-based selector with outline support
        if hasattr(self.selector, 'draw_to_mask') and hasattr(self, '_current_hole') and hasattr(self, '_current_feature_type'):
            if self._fill_mode:
                # Fill mode: generate filled polygon and AUTO-MERGE with last mask
                print(f"[FILL MODE] Processing {len(self._draw_points)} draw points")
                if hasattr(self.selector, 'fill_and_merge'):
                    # Use auto-merge fill if available
                    mask_data = self.selector.fill_and_merge(
                        self._draw_points,
                        self._last_generated_mask_id,  # Merge with this mask
                        self._current_hole,
                        self._current_feature_type
                    )
                    if mask_data:
                        # Remove old mask from selection if it was replaced
                        if self._last_generated_mask_id and self._last_generated_mask_id in self.selected_mask_ids:
                            self.selected_mask_ids.remove(self._last_generated_mask_id)
                        self._last_generated_mask_id = mask_data.id
                        if mask_data.id not in self.selected_mask_ids:
                            self.selected_mask_ids.append(mask_data.id)
                        logger.info(f"Fill merged into: {mask_data.id}")
                        print(f"[FILL MODE] Merged into: {mask_data.id}")
                    else:
                        logger.warning("Failed to fill and merge")
                        print("[FILL MODE] Failed - draw a larger area")
                elif hasattr(self.selector, 'fill_polygon_to_mask'):
                    # Fallback to separate fill
                    mask_data = self.selector.fill_polygon_to_mask(
                        self._draw_points,
                        self._current_hole,
                        self._current_feature_type
                    )
                    if mask_data:
                        self._last_generated_mask_id = mask_data.id
                        if mask_data.id not in self.selected_mask_ids:
                            self.selected_mask_ids.append(mask_data.id)
                        logger.info(f"Generated filled polygon: {mask_data.id}")
                        print(f"[FILL MODE] Created separate fill: {mask_data.id}")
                    else:
                        logger.warning("Failed to generate filled polygon")
                        print("[FILL MODE] Failed to generate filled polygon")
                else:
                    logger.warning("Fill mode not supported by this selector")
                    print("[FILL MODE] Not supported by this selector")
            else:
                # SAM mode: generate mask from outline with SAM processing
                mask_data = self.selector.draw_to_mask(
                    self._draw_points,
                    self._current_hole,
                    self._current_feature_type
                )
                if mask_data:
                    # Track this as the last generated mask for undo
                    self._last_generated_mask_id = mask_data.id
                    # Add to selected masks
                    if mask_data.id not in self.selected_mask_ids:
                        self.selected_mask_ids.append(mask_data.id)
                    logger.info(f"Generated mask from outline: {mask_data.id}")
                else:
                    logger.warning("Failed to generate mask from outline")
        
        # Clear drawing visualization
        if self._draw_line is not None:
            self._draw_line.remove()
            self._draw_line = None
        
        # Clear draw points
        self._draw_points = []
        
        # Process events after mask generation to keep GUI responsive
        try:
            self.fig.canvas.flush_events()
        except:
            pass
        
        # Redraw to show the new mask
        self._redraw()
    
    def _on_click(self, event):
        """Handle mouse click events (single click fallback)."""
        # This is now a fallback - drawing is preferred
        # Only trigger if not in drawing mode
        if self._drawing:
            return
        
        # Check if button was clicked
        if hasattr(event, 'inaxes') and event.inaxes != self.ax:
            return
        
        if event.button != 1:  # Only left mouse button
            return
        
        # Get click coordinates in image space
        if event.inaxes == self.ax:
            if event.xdata is None or event.ydata is None:
                return
            
            x = int(event.xdata)
            y = int(event.ydata)
            
            # Validate coordinates are within image bounds
            image = self.selector.image
            if x < 0 or x >= image.shape[1] or y < 0 or y >= image.shape[0]:
                logger.warning(f"Click outside image bounds: ({x}, {y})")
                return
            
            # For point-based selector, single click is now just a fallback
            # Drawing is the preferred method
            if hasattr(self.selector, 'click_to_mask') and hasattr(self, '_current_hole') and hasattr(self, '_current_feature_type'):
                mask_data = self.selector.click_to_mask(
                    x, y,
                    self._current_hole,
                    self._current_feature_type
                )
                if mask_data:
                    self._last_generated_mask_id = mask_data.id
                    if mask_data.id not in self.selected_mask_ids:
                        self.selected_mask_ids.append(mask_data.id)
                    self._redraw()
                    if self.click_callback:
                        self.click_callback(mask_data.id)
            else:
                # Original mask selection mode
                mask_id = self.selector.get_mask_at_point(x, y)
                
                if mask_id:
                    if mask_id in self.selected_mask_ids:
                        self.selected_mask_ids.remove(mask_id)
                        logger.info(f"Deselected mask: {mask_id}")
                    else:
                        self.selected_mask_ids.append(mask_id)
                        logger.info(f"Selected mask: {mask_id}")
                    
                    self._redraw()
                    
                    if self.click_callback:
                        self.click_callback(mask_id)
                else:
                    logger.warning(f"No mask found at ({x}, {y})")
    
    def _on_done(self, event):
        """Handle Done button press."""
        self._done_pressed = True
        if self.done_callback:
            self.done_callback()
    
    def _on_scroll(self, event):
        """Handle mouse wheel scroll for zooming."""
        if event.inaxes != self.ax:
            return
        
        # Get the current x and y limits
        cur_xlim = self.ax.get_xlim()
        cur_ylim = self.ax.get_ylim()
        
        # Get the event location in data coordinates
        xdata = event.xdata
        ydata = event.ydata
        
        if xdata is None or ydata is None:
            return
        
        # Zoom factor - make zoom more responsive
        if event.button == 'up':
            # Zoom in (more aggressive)
            scale_factor = 0.85
        elif event.button == 'down':
            # Zoom out (more aggressive)
            scale_factor = 1.15
        else:
            return
        
        # Calculate new limits centered on the mouse position
        new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
        new_height = (cur_ylim[0] - cur_ylim[1]) * scale_factor  # Note: ylim is inverted
        
        # Center the zoom on the mouse position
        relx = (xdata - cur_xlim[0]) / (cur_xlim[1] - cur_xlim[0])
        rely = (ydata - cur_ylim[0]) / (cur_ylim[1] - cur_ylim[0])
        
        new_xlim = [xdata - new_width * relx, xdata + new_width * (1 - relx)]
        new_ylim = [ydata + new_height * rely, ydata - new_height * (1 - rely)]  # Inverted
        
        # Apply limits but keep within image bounds
        image = self.selector.image
        height, width = image.shape[:2]
        
        # Clamp to image bounds
        new_xlim[0] = max(0, min(new_xlim[0], width))
        new_xlim[1] = max(0, min(new_xlim[1], width))
        new_ylim[0] = max(0, min(new_ylim[0], height))
        new_ylim[1] = max(0, min(new_ylim[1], height))
        
        # Ensure we don't zoom out beyond image bounds
        if new_xlim[1] - new_xlim[0] > width:
            new_xlim = [0, width]
        if abs(new_ylim[1] - new_ylim[0]) > height:
            new_ylim = [height, 0]
        
        self.ax.set_xlim(new_xlim)
        self.ax.set_ylim(new_ylim)
        self.fig.canvas.draw_idle()
    
    def _on_key(self, event):
        """Handle keyboard events."""
        if event.key == 'enter' or event.key == ' ':
            # Enter or Space = Done
            self._done_pressed = True
            if self.done_callback:
                self.done_callback()
        elif event.key == 'f':
            # F = Toggle fill mode
            self._fill_mode = not self._fill_mode
            mode_name = "FILL (polygon)" if self._fill_mode else "SAM (outline)"
            logger.info(f"Switched to {mode_name} mode")
            self._redraw()  # Redraw to update mode indicator
        elif event.key == 'm':
            # M = Merge selected masks
            if len(self.selected_mask_ids) >= 2:
                if hasattr(self.selector, 'merge_selected_masks') and hasattr(self, '_current_hole') and hasattr(self, '_current_feature_type'):
                    merged = self.selector.merge_selected_masks(
                        self.selected_mask_ids.copy(),
                        self._current_hole,
                        self._current_feature_type
                    )
                    if merged:
                        # Clear old selections and select merged mask
                        self.selected_mask_ids.clear()
                        self.selected_mask_ids.append(merged.id)
                        self._last_generated_mask_id = merged.id
                        logger.info(f"Merged masks into: {merged.id}")
                        self._redraw()
                    else:
                        logger.warning("Failed to merge masks")
                else:
                    logger.warning("Merge not supported by this selector")
            else:
                logger.info("Select at least 2 masks to merge (press M again after selecting)")
        elif event.key == 'escape':
            # Escape = Undo last generated mask (for point-based) or clear selection
            if hasattr(self.selector, 'click_to_mask') and self._last_generated_mask_id:
                # Point-based mode: remove last generated mask
                mask_id = self._last_generated_mask_id
                
                # Remove from selected masks
                if mask_id in self.selected_mask_ids:
                    self.selected_mask_ids.remove(mask_id)
                
                # Remove from generated_masks
                if hasattr(self.selector, 'generated_masks') and mask_id in self.selector.generated_masks:
                    del self.selector.generated_masks[mask_id]
                
                # Remove from selections
                if hasattr(self.selector, 'selections'):
                    for hole, selection in self.selector.selections.items():
                        if hasattr(selection, 'greens') and mask_id in selection.greens:
                            selection.greens.remove(mask_id)
                        if hasattr(selection, 'tees') and mask_id in selection.tees:
                            selection.tees.remove(mask_id)
                        if hasattr(selection, 'fairways') and mask_id in selection.fairways:
                            selection.fairways.remove(mask_id)
                        if hasattr(selection, 'bunkers') and mask_id in selection.bunkers:
                            selection.bunkers.remove(mask_id)
                
                # Clear last generated mask tracking
                self._last_generated_mask_id = None
                
                # Update display
                self._redraw()
                logger.info(f"Undid last mask generation: {mask_id}")
            else:
                # Fallback: clear all selections
                self.selected_mask_ids.clear()
                self._redraw()
    
    def _redraw(self):
        """Redraw the visualization with current selections."""
        if self.ax is None or self.fig is None:
            return  # Cannot redraw if window not initialized
        
        image = self.selector.image
        
        # Get masks - either from selector.masks or from generated_masks
        if hasattr(self.selector, 'generated_masks'):
            # Point-based selector
            masks = list(self.selector.generated_masks.values())
        else:
            # Original selector
            masks = list(self.selector.masks.values())
        
        overlay = create_mask_overlay(image, masks, self.selected_mask_ids)
        
        # Save current zoom/pan state before updating
        current_xlim = self.ax.get_xlim() if self.ax is not None else None
        current_ylim = self.ax.get_ylim() if self.ax is not None else None
        
        # Check if we have an existing image to update (more efficient than clearing)
        if hasattr(self, '_image_artist') and self._image_artist is not None:
            # Update existing image data instead of clearing and redrawing
            self._image_artist.set_array(overlay)
        else:
            # First time - create image artist
            height, width = overlay.shape[:2]
            self._image_artist = self.ax.imshow(overlay, extent=[0, width, height, 0], origin='upper')
            self.ax.set_title(self.title, fontsize=14, pad=20)
            self.ax.axis('on')
            self.ax.set_facecolor('black')
            
            # Set initial limits
            if current_xlim is None or current_ylim is None:
                self.ax.set_xlim(0, width)
                self.ax.set_ylim(height, 0)  # Inverted Y axis (origin='upper')
        
        # Restore zoom/pan state if it was set
        if current_xlim is not None and current_ylim is not None:
            height, width = overlay.shape[:2]
            # Validate that saved limits are still within image bounds
            xlim_valid = (0 <= current_xlim[0] <= width and 0 <= current_xlim[1] <= width and
                         current_xlim[0] < current_xlim[1])
            ylim_valid = (0 <= current_ylim[0] <= height and 0 <= current_ylim[1] <= height and
                         current_ylim[0] > current_ylim[1])  # Inverted Y axis
            
            if xlim_valid and ylim_valid:
                self.ax.set_xlim(current_xlim)
                self.ax.set_ylim(current_ylim)
        
        # Add mask ID labels at centroids
        for i, mask_data in enumerate(masks):
            y_coords, x_coords = np.where(mask_data.mask)
            if len(y_coords) > 0:
                centroid_x = int(x_coords.mean())
                centroid_y = int(y_coords.mean())
                # Get mask index - support both InteractiveSelector and PointBasedSelector
                if hasattr(self.selector, '_mask_id_to_index'):
                    mask_idx = self.selector._mask_id_to_index.get(mask_data.id, i)
                else:
                    # For PointBasedSelector, use index in generated_masks
                    mask_idx = i
                is_selected = mask_data.id in self.selected_mask_ids
                color = 'lime' if is_selected else 'white'
                weight = 'bold' if is_selected else 'normal'
                # Only add text labels if we're doing a full redraw (not just updating image)
                if not hasattr(self, '_text_artists'):
                    self._text_artists = []
                
                # For now, skip text labels on updates to avoid blinking
                # We can add them back if needed, but they cause redraw issues
                pass
        
        # Update the instructions panel on the left
        self._update_instructions()
        
        # Use draw_idle for smoother updates (non-blocking)
        self.fig.canvas.draw_idle()
    
    def show(self, block: bool = True):
        """
        Display the interactive selector.
        
        Args:
            block: If True, blocks until done (via button/keyboard)
        """
        image = self.selector.image
        # Get masks - either from selector.masks or from generated_masks
        if hasattr(self.selector, 'generated_masks'):
            # Point-based selector
            masks = list(self.selector.generated_masks.values())
        else:
            # Original selector
            masks = list(self.selector.masks.values())
        
        # Create figure with instructions panel on left, image on right
        self.fig = plt.figure(figsize=(18, 12))
        
        # Left panel for instructions (fixed width)
        self.ax_instructions = self.fig.add_axes([0.01, 0.05, 0.14, 0.90])
        self.ax_instructions.set_facecolor('#f0f0f0')
        self.ax_instructions.set_xticks([])
        self.ax_instructions.set_yticks([])
        self._setup_instructions_panel()
        
        # Main image axes (to the right of instructions)
        self.ax = self.fig.add_axes([0.16, 0.05, 0.83, 0.93])
        
        # Enable mouse wheel zoom explicitly
        # Connect scroll event for zoom
        self.fig.canvas.mpl_connect('scroll_event', self._on_scroll)
        
        # Note: We don't need to show image here, _redraw() will do it
        # Just set up the axes and UI components first
        
        self.ax.set_title(self.title, fontsize=14, pad=20)
        self.ax.axis('off')
        
        # Add Done button
        ax_button = self.fig.add_axes([0.85, 0.01, 0.13, 0.03])
        self.done_button = Button(ax_button, 'Done (Enter/Space)', color='lightgreen', hovercolor='green')
        self.done_button.on_clicked(self._on_done)
        
        # Connect event handlers
        # Drawing mode: press to start, motion to draw, release to finish
        self.fig.canvas.mpl_connect('button_press_event', self._on_press)
        self.fig.canvas.mpl_connect('motion_notify_event', self._on_motion)
        self.fig.canvas.mpl_connect('button_release_event', self._on_release)
        self.fig.canvas.mpl_connect('key_press_event', self._on_key)
        
        # Set window title (Qt uses setWindowTitle, Tk uses set_window_title)
        try:
            self.fig.canvas.set_window_title(self.title)
        except AttributeError:
            try:
                self.fig.canvas.setWindowTitle(self.title)
            except AttributeError:
                pass  # Some backends don't support window title
        
        # Connect keyboard events (focus handling varies by backend)
        try:
            # Qt uses setFocus, Tk might use set_focus
            if hasattr(self.fig.canvas, 'setFocus'):
                self.fig.canvas.mpl_connect('figure_enter_event', lambda e: self.fig.canvas.setFocus())
            elif hasattr(self.fig.canvas, 'set_focus'):
                self.fig.canvas.mpl_connect('figure_enter_event', lambda e: self.fig.canvas.set_focus())
        except AttributeError:
            pass  # Focus handling not critical for tests
        
        # Initial display - this will show the image with masks
        self._redraw()
        
        # Show window first (non-blocking) so it can render
        plt.ion()  # Turn on interactive mode
        plt.show(block=False)
        
        # Force canvas update to ensure image is fully rendered and visible
        self.fig.canvas.draw_idle()  # Queue a redraw
        self.fig.canvas.flush_events()  # Process all pending events
        import time
        time.sleep(0.1)  # Small delay to allow window to fully render
        
        # Show and wait for done if blocking
        if block:
            
            # Wait for done signal with frequent event processing
            while not self._done_pressed:
                try:
                    self.fig.canvas.flush_events()
                except:
                    pass
                plt.pause(0.2)  # Longer pause to reduce CPU and prevent "not responding"
            
            # Don't close the figure - just reset the done flag
            # This allows the same window to be reused for the next feature
            self._done_pressed = False  # Reset for next use
            # Note: Figure is NOT closed, caller should handle cleanup if needed
        else:
            plt.show(block=False)
    
    def get_selected_mask_ids(self) -> List[str]:
        """Get currently selected mask IDs."""
        return self.selected_mask_ids.copy()
    
    def clear_selection(self):
        """Clear current selection."""
        self.selected_mask_ids.clear()
        if self.fig:
            self._redraw()
    
    def set_callback(self, callback: Callable[[str], None]):
        """Set callback function called when mask is clicked."""
        self.click_callback = callback
    
    def set_done_callback(self, callback: Callable[[], None]):
        """Set callback function called when Done is pressed."""
        self.done_callback = callback
    
    def is_done(self) -> bool:
        """Check if done has been pressed."""
        return self._done_pressed
    
    def reset_done(self):
        """Reset the done flag."""
        self._done_pressed = False
    
    def update_title(self, title: str):
        """Update the window title."""
        self.title = title
        if self.ax:
            self._redraw()


def visualize_masks_matplotlib(
    selector: InteractiveSelector,
    selected_mask_ids: Optional[List[str]] = None,
    title: str = "Click on masks to select",
) -> InteractiveMaskSelector:
    """
    Display image with masks using matplotlib for interactive selection.
    
    Args:
        selector: InteractiveSelector instance
        selected_mask_ids: Currently selected mask IDs
        title: Window title
        
    Returns:
        InteractiveMaskSelector instance for further interaction
    """
    if not MATPLOTLIB_AVAILABLE:
        raise ImportError("matplotlib is required for interactive visualization")
    
    interactive = InteractiveMaskSelector(selector, title)
    if selected_mask_ids:
        interactive.selected_mask_ids = selected_mask_ids.copy()
    
    return interactive


def get_mask_bounds(masks: List[MaskData]) -> Tuple[int, int, int, int]:
    """
    Get bounding box that encompasses all masks.
    
    Returns:
        (min_x, min_y, max_x, max_y)
    """
    if not masks:
        return 0, 0, 0, 0
    
    min_x = min(m.bbox[0] for m in masks)
    min_y = min(m.bbox[1] for m in masks)
    max_x = max(m.bbox[0] + m.bbox[2] for m in masks)
    max_y = max(m.bbox[1] + m.bbox[3] for m in masks)
    
    return min_x, min_y, max_x, max_y


def save_mask_preview(
    image: np.ndarray,
    masks: List[MaskData],
    output_path: Path,
    selected_mask_ids: Optional[List[str]] = None,
) -> None:
    """
    Save a static preview image with masks overlaid.
    
    Args:
        image: Source image
        masks: List of masks
        output_path: Path to save preview
        selected_mask_ids: Selected masks to highlight
    """
    try:
        from PIL import Image
    except ImportError:
        logger.warning("PIL not available, cannot save preview")
        return
    
    overlay = create_mask_overlay(image, masks, selected_mask_ids)
    preview_img = Image.fromarray(overlay)
    preview_img.save(output_path)
    
    logger.info(f"Saved mask preview to {output_path}")
