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
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

from .masks import MaskData
from .interactive import InteractiveSelector, FeatureType

logger = logging.getLogger(__name__)


def create_mask_overlay(
    image: np.ndarray,
    masks: List[MaskData],
    selected_mask_ids: Optional[List[str]] = None,
    alpha: float = 0.5,
) -> np.ndarray:
    """
    Create an overlay visualization showing masks on the image.
    
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
    
    for mask_data in masks:
        mask = mask_data.mask
        is_selected = mask_data.id in selected_ids
        
        # Choose color: red for selected, yellow for unselected
        if is_selected:
            color = np.array([255, 0, 0])  # Red
            mask_alpha = alpha * 0.8  # More opaque for selected
        else:
            color = np.array([255, 255, 0])  # Yellow
            mask_alpha = alpha * 0.3  # Less opaque for unselected
        
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
        
    def _on_click(self, event):
        """Handle mouse click events."""
        # Check if button was clicked
        if hasattr(event, 'inaxes') and event.inaxes != self.ax:
            return
        
        if event.button != 1:  # Only left mouse button
            return
        
        # Get click coordinates in image space
        if event.inaxes == self.ax:
            x = int(event.xdata)
            y = int(event.ydata)
            
            # Find mask at clicked point
            mask_id = self.selector.get_mask_at_point(x, y)
            
            if mask_id:
                # Toggle selection
                if mask_id in self.selected_mask_ids:
                    self.selected_mask_ids.remove(mask_id)
                    logger.info(f"Deselected mask: {mask_id}")
                else:
                    self.selected_mask_ids.append(mask_id)
                    logger.info(f"Selected mask: {mask_id}")
                
                # Update display
                self._redraw()
                
                # Call callback if provided
                if self.click_callback:
                    self.click_callback(mask_id)
            else:
                logger.warning(f"No mask found at ({x}, {y})")
    
    def _on_done(self, event):
        """Handle Done button press."""
        self._done_pressed = True
        if self.done_callback:
            self.done_callback()
    
    def _on_key(self, event):
        """Handle keyboard events."""
        if event.key == 'enter' or event.key == ' ':
            # Enter or Space = Done
            self._done_pressed = True
            if self.done_callback:
                self.done_callback()
        elif event.key == 'escape':
            # Escape = Clear selection
            self.selected_mask_ids.clear()
            self._redraw()
    
    def _redraw(self):
        """Redraw the visualization with current selections."""
        if self.ax is None or self.fig is None:
            return  # Cannot redraw if window not initialized
        
        image = self.selector.image
        masks = list(self.selector.masks.values())
        
        overlay = create_mask_overlay(image, masks, self.selected_mask_ids)
        
        self.ax.clear()
        # Ensure image is in correct format for matplotlib (RGB, not BGR)
        # imshow expects RGB for uint8 arrays
        self.ax.imshow(overlay)
        self.ax.set_title(self.title, fontsize=14, pad=20)
        self.ax.axis('off')
        
        # Add mask ID labels at centroids
        for mask_data in masks:
            y_coords, x_coords = np.where(mask_data.mask)
            if len(y_coords) > 0:
                centroid_x = int(x_coords.mean())
                centroid_y = int(y_coords.mean())
                mask_idx = self.selector._mask_id_to_index.get(mask_data.id, -1)
                is_selected = mask_data.id in self.selected_mask_ids
                color = 'lime' if is_selected else 'white'
                weight = 'bold' if is_selected else 'normal'
                self.ax.text(centroid_x, centroid_y, f"{mask_idx}", 
                           color=color, fontsize=8, ha='center', va='center',
                           weight=weight,
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='black', alpha=0.7))
        
        # Add legend for selected count and instructions
        info_text = f"Selected: {len(self.selected_mask_ids)}"
        if self.selected_mask_ids:
            self.ax.text(0.02, 0.98, info_text,
                        transform=self.ax.transAxes,
                        fontsize=12, verticalalignment='top',
                        bbox=dict(boxstyle='round', facecolor='green', alpha=0.7))
        
        # Add keyboard shortcuts info
        shortcuts_text = "Click masks to select | Enter/Space: Done | Esc: Clear"
        self.ax.text(0.5, 0.02, shortcuts_text,
                    transform=self.ax.transAxes,
                    fontsize=10, horizontalalignment='center',
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        self.fig.canvas.draw()
    
    def show(self, block: bool = True):
        """
        Display the interactive selector.
        
        Args:
            block: If True, blocks until done (via button/keyboard)
        """
        image = self.selector.image
        masks = list(self.selector.masks.values())
        
        # Create figure with space for button
        self.fig = plt.figure(figsize=(16, 13))
        
        # Main image axes
        self.ax = self.fig.add_axes([0, 0.05, 1, 0.93])  # Leave space at bottom for button
        
        # Note: We don't need to show image here, _redraw() will do it
        # Just set up the axes and UI components first
        
        self.ax.set_title(self.title, fontsize=14, pad=20)
        self.ax.axis('off')
        
        # Add Done button
        ax_button = self.fig.add_axes([0.85, 0.01, 0.13, 0.03])
        self.done_button = Button(ax_button, 'Done (Enter/Space)', color='lightgreen', hovercolor='green')
        self.done_button.on_clicked(self._on_done)
        
        # Connect event handlers
        self.fig.canvas.mpl_connect('button_press_event', self._on_click)
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
            
            # Wait for done signal
            while not self._done_pressed:
                plt.pause(0.1)  # Small pause to allow event processing
            
            plt.close(self.fig)
            self._done_pressed = False  # Reset for next use
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
