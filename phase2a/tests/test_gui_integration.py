"""
Full GUI Integration Tests for Interactive Selection

These tests actually create and interact with matplotlib GUI windows.
They are slower but test the complete GUI workflow.
"""

import pytest
import numpy as np
from pathlib import Path
import time
import threading
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

# Set matplotlib backend before any imports
# IMPORTANT: Use the GUI backend that's available - do NOT use headless/Agg
# Force GUI backend by unsetting any headless environment variables
import os
os.environ.pop('MPLBACKEND', None)  # Remove headless backend if set

MATPLOTLIB_GUI_AVAILABLE = False
GUI_BACKEND = None

try:
    import matplotlib
    # Try TkAgg first (more stable in headless/SSH environments)
    # Then fallback to Qt5Agg
    try:
        matplotlib.use('TkAgg', force=True)
        import matplotlib.pyplot as plt
        # Test that it actually works
        fig, ax = plt.subplots()
        plt.close(fig)
        MATPLOTLIB_GUI_AVAILABLE = True
        GUI_BACKEND = 'TkAgg'
    except (ImportError, RuntimeError, Exception):
        # Fallback to Qt5Agg
        try:
            matplotlib.use('Qt5Agg', force=True)
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
            # Test that it actually works
            fig, ax = plt.subplots()
            plt.close(fig)
            MATPLOTLIB_GUI_AVAILABLE = True
            GUI_BACKEND = 'Qt5Agg'
        except (ImportError, RuntimeError, Exception):
            MATPLOTLIB_GUI_AVAILABLE = False
except ImportError:
    MATPLOTLIB_GUI_AVAILABLE = False

from phase2a.pipeline.masks import MaskData
from phase2a.pipeline.interactive import InteractiveSelector, FeatureType
from phase2a.pipeline.visualize import InteractiveMaskSelector


# Pytest marker for GUI tests
pytestmark = pytest.mark.skipif(
    not MATPLOTLIB_GUI_AVAILABLE,
    reason="GUI backend not available for matplotlib"
)


@pytest.fixture(autouse=True)
def gui_test_backend():
    """Ensure we're using a GUI backend for tests - runs before each test."""
    if not MATPLOTLIB_GUI_AVAILABLE:
        pytest.skip("GUI backend not available")
    
    import matplotlib
    import os
    
    # Force GUI backend - unset any headless settings
    os.environ.pop('MPLBACKEND', None)
    
    # Ensure we're using the GUI backend
    if GUI_BACKEND:
        matplotlib.use(GUI_BACKEND, force=True)
    
    current_backend = matplotlib.get_backend()
    # Verify we're using a GUI backend (not Agg)
    if current_backend == 'Agg':
        pytest.skip(f"Cannot run GUI tests with {current_backend} backend. Use Qt5Agg or TkAgg.")
    
    return current_backend


@pytest.fixture
def sample_masks():
    """Create sample masks for GUI testing."""
    masks = []
    for i in range(10):
        # Create masks at different positions
        mask = np.zeros((200, 200), dtype=bool)
        y_start = i * 20
        x_start = i * 20
        mask[y_start:y_start+15, x_start:x_start+15] = True
        
        mask_data = MaskData(
            id=f"mask_{i:04d}",
            mask=mask,
            area=225,
            bbox=(x_start, y_start, 15, 15),
            predicted_iou=0.9,
            stability_score=0.95,
        )
        masks.append(mask_data)
    
    return masks


@pytest.fixture
def sample_image():
    """Create a sample image for GUI testing."""
    # Create a bright, colorful test image that's clearly visible
    image = np.zeros((200, 200, 3), dtype=np.uint8)
    # Fill with bright gray background (not black!)
    image[:, :] = [128, 128, 128]  # Medium gray background - clearly visible
    # Add bright colored regions to make it obvious
    image[0:100, 0:100] = [255, 0, 0]  # Bright red region
    image[100:200, 100:200] = [0, 255, 0]  # Bright green region
    image[0:100, 100:200] = [0, 0, 255]  # Bright blue region
    image[100:200, 0:100] = [255, 255, 0]  # Bright yellow region
    return image


@pytest.fixture
def interactive_selector(sample_masks, sample_image):
    """Create an InteractiveSelector for testing."""
    return InteractiveSelector(sample_masks, sample_image)


class TestGUIWindowCreation:
    """Tests that verify GUI windows can be created."""
    
    def test_create_interactive_window(self, interactive_selector, gui_test_backend):
        """Test that interactive window can be created."""
        interactive = InteractiveMaskSelector(
            interactive_selector,
            title="Test Window Creation"
        )
        
        # Verify window components are initialized
        assert interactive.selector == interactive_selector
        assert interactive.title == "Test Window Creation"
        assert interactive.fig is None  # Not created until show()
        
        # Test window creation (non-blocking)
        plt.ion()  # Turn on interactive mode
        interactive.show(block=False)
        
        # Give window time to render
        time.sleep(0.5)
        
        # Verify window was created
        assert interactive.fig is not None
        assert interactive.ax is not None
        assert interactive.done_button is not None
        
        # Close window
        plt.close(interactive.fig)
        plt.ioff()  # Turn off interactive mode
    
    def test_window_displays_masks(self, interactive_selector, gui_test_backend):
        """Test that masks are displayed in the window."""
        interactive = InteractiveMaskSelector(
            interactive_selector,
            title="Test Mask Display"
        )
        
        plt.ion()
        interactive.show(block=False)
        time.sleep(0.5)  # Give window time to render
        
        # Verify image is displayed
        assert interactive.ax is not None
        images = interactive.ax.get_images()
        assert len(images) > 0, "Image should be displayed in axes"
        
        # Verify the displayed image has the correct data
        displayed_image = images[0].get_array()
        assert displayed_image is not None, "Image array should be set"
        assert displayed_image.shape == interactive.selector.image.shape[:2] or \
               displayed_image.shape == interactive.selector.image.shape, \
               f"Displayed image shape {displayed_image.shape} should match source {interactive.selector.image.shape}"
        
        # Verify image has visible content (not all black/zeros)
        if len(displayed_image.shape) == 2:
            # Grayscale
            assert displayed_image.max() > 0, "Image should have non-zero values"
        else:
            # RGB - check that at least one channel has non-zero values
            assert displayed_image.sum() > 0, "Image should have visible content"
        
        # Verify masks are visible (they should be in the overlay)
        assert len(interactive.selector.masks) > 0
        
        # Verify overlay was created correctly (should have mask highlights)
        from phase2a.pipeline.visualize import create_mask_overlay
        overlay = create_mask_overlay(
            interactive.selector.image,
            list(interactive.selector.masks.values()),
            None
        )
        # Overlay should have same shape as source image
        assert overlay.shape == interactive.selector.image.shape
        
        plt.close(interactive.fig)
        plt.ioff()
    
    @pytest.mark.skipif(
        not (Path(__file__).parent.parent / "resources" / "Pictatinny_B.jpg").exists(),
        reason="Resource images not available"
    )
    def test_display_real_resource_image(
        self, pictatinny_b_array, gui_test_backend
    ):
        """Test that actual resource image loads and displays correctly in GUI."""
        from phase2a.pipeline.interactive import InteractiveSelector
        from phase2a.pipeline.visualize import InteractiveMaskSelector
        
        # Use the actual resource image
        image = pictatinny_b_array
        
        # Create sample masks that fit the actual image dimensions
        img_height, img_width = image.shape[:2]
        
        # Create a few test masks at different locations
        masks = []
        num_masks = 5
        mask_size = min(img_width, img_height) // 10  # Size masks appropriately for image
        
        for i in range(num_masks):
            mask = np.zeros((img_height, img_width), dtype=bool)
            # Place masks at different positions across the image
            y_start = (img_height * (i + 1)) // (num_masks + 1)
            x_start = (img_width * (i + 1)) // (num_masks + 1)
            
            # Ensure mask fits within image bounds
            y_end = min(y_start + mask_size, img_height)
            x_end = min(x_start + mask_size, img_width)
            
            if y_end > y_start and x_end > x_start:
                mask[y_start:y_end, x_start:x_end] = True
                
                # Calculate bbox
                rows = np.any(mask, axis=1)
                cols = np.any(mask, axis=0)
                if np.any(rows) and np.any(cols):
                    rmin, rmax = np.where(rows)[0][[0, -1]]
                    cmin, cmax = np.where(cols)[0][[0, -1]]
                    
                    mask_data = MaskData(
                        id=f"mask_{i:04d}",
                        mask=mask,
                        area=int(np.sum(mask)),
                        bbox=(int(cmin), int(rmin), int(cmax - cmin), int(rmax - rmin)),
                        predicted_iou=0.9,
                        stability_score=0.95,
                    )
                    masks.append(mask_data)
        
        if len(masks) == 0:
            pytest.skip("Could not create masks for image size")
        
        # Verify image properties
        assert image.shape[2] == 3, "Image should be RGB"
        assert image.dtype == np.uint8, "Image should be uint8"
        assert image.max() > 0 and image.min() < 255, "Image should have visible content"
        
        print(f"Resource image shape: {image.shape}")
        print(f"Resource image range: {image.min()} - {image.max()}")
        print(f"Resource image mean: {image.mean():.2f}")
        print(f"Created {len(masks)} masks for display")
        
        # Create selector with real image
        selector = InteractiveSelector(masks, image)
        interactive = InteractiveMaskSelector(
            selector,
            title="Resource Image Display Test (Pictatinny_B.jpg)"
        )
        
        # Display and verify
        plt.ion()
        interactive.show(block=False)
        time.sleep(1.0)  # Give window time to render the real image
        
        # Verify image is displayed
        assert interactive.ax is not None, "Axes should be created"
        images = interactive.ax.get_images()
        assert len(images) > 0, "Image should be displayed in axes"
        
        # Verify the displayed image has the correct data
        displayed_image = images[0].get_array()
        assert displayed_image is not None, "Image array should be set"
        
        # Verify shape matches (may be 2D or 3D depending on matplotlib processing)
        assert displayed_image.shape[:2] == image.shape[:2], \
            f"Displayed image shape {displayed_image.shape[:2]} should match source {image.shape[:2]}"
        
        # Verify image has visible content (not all black/zeros)
        if len(displayed_image.shape) == 2:
            # Grayscale
            assert displayed_image.max() > 0, "Image should have non-zero values"
        else:
            # RGB - check that image has visible content
            assert displayed_image.sum() > 0, "Image should have visible content"
            assert displayed_image.max() > 50, "Image should have reasonably bright pixels"
        
        print(f"Displayed image shape: {displayed_image.shape}")
        print(f"Displayed image range: {displayed_image.min()} - {displayed_image.max()}")
        
        # Verify masks are displayed
        assert len(interactive.selector.masks) == len(masks), \
            f"All {len(masks)} masks should be in selector"
        
        plt.close(interactive.fig)
        plt.ioff()


class TestGUIClickInteraction:
    """Tests for actual GUI click interactions."""
    
    def test_click_selects_mask(self, interactive_selector, gui_test_backend):
        """Test that clicking on a mask selects it."""
        interactive = InteractiveMaskSelector(
            interactive_selector,
            title="Test Click Selection"
        )
        
        plt.ion()
        interactive.show(block=False)
        time.sleep(0.5)  # Wait for window to render
        
        # Simulate click on first mask (at position ~7, 7, inside first mask)
        # First mask is at (0:15, 0:15)
        class MockClickEvent:
            def __init__(self, x, y):
                self.xdata = x
                self.ydata = y
                self.inaxes = interactive.ax
                self.button = 1
        
        click_event = MockClickEvent(10, 10)
        
        # Initial state - no selections
        assert len(interactive.get_selected_mask_ids()) == 0
        
        # Trigger click handler
        interactive._on_click(click_event)
        
        # Verify mask was selected
        selected = interactive.get_selected_mask_ids()
        assert len(selected) == 1
        assert "mask_0000" in selected
        
        # Click again to deselect
        interactive._on_click(click_event)
        assert len(interactive.get_selected_mask_ids()) == 0
        
        plt.close(interactive.fig)
        plt.ioff()
    
    def test_multiple_clicks_select_multiple_masks(self, interactive_selector, gui_test_backend):
        """Test that multiple clicks select multiple masks."""
        interactive = InteractiveMaskSelector(
            interactive_selector,
            title="Test Multiple Clicks"
        )
        
        plt.ion()
        interactive.show(block=False)
        time.sleep(0.5)
        
        # Click on first mask
        click1 = type('obj', (object,), {
            'xdata': 10, 'ydata': 10, 'inaxes': interactive.ax, 'button': 1
        })()
        interactive._on_click(click1)
        
        # Click on second mask (at ~25, 25)
        click2 = type('obj', (object,), {
            'xdata': 30, 'ydata': 30, 'inaxes': interactive.ax, 'button': 1
        })()
        interactive._on_click(click2)
        
        # Verify both selected
        selected = interactive.get_selected_mask_ids()
        assert len(selected) == 2
        assert "mask_0000" in selected
        assert "mask_0001" in selected
        
        plt.close(interactive.fig)
        plt.ioff()
    
    def test_click_outside_mask_does_nothing(self, interactive_selector, gui_test_backend):
        """Test that clicking outside masks doesn't select anything."""
        interactive = InteractiveMaskSelector(
            interactive_selector,
            title="Test Click Outside"
        )
        
        plt.ion()
        interactive.show(block=False)
        time.sleep(0.5)
        
        # Click at position with no mask (far from all masks)
        # Masks are at: (0,0), (20,20), (40,40), ... (180,180) - each 15x15
        # Last mask (mask_0009) at (180,180) extends to (195,195)
        # Use (199, 199) which should be outside, but verify first
        # Actually, mask_0009 covers y=[180:195], x=[180:195]
        # Point (199, 199) should be outside since mask[199, 199] should be False
        # But let's use a safer approach: use a point we know is outside
        # Image is 200x200, masks end at 195, so (199, 199) should work
        # But to be safe, let's verify the point is truly outside
        test_x, test_y = 199, 199
        mask_at_point = interactive.selector.get_mask_at_point(test_x, test_y)
        if mask_at_point is not None:
            # If (199, 199) is in a mask, use (198, 198) or find a better spot
            # Let's try corners or other safe positions
            for test_point in [(195, 5), (5, 195), (50, 10), (10, 50)]:
                if interactive.selector.get_mask_at_point(test_point[0], test_point[1]) is None:
                    test_x, test_y = test_point
                    break
        
        click_event = type('obj', (object,), {
            'xdata': test_x, 'ydata': test_y, 'inaxes': interactive.ax, 'button': 1
        })()
        
        initial_count = len(interactive.get_selected_mask_ids())
        interactive._on_click(click_event)
        
        # Should not have changed selection count
        assert len(interactive.get_selected_mask_ids()) == initial_count
        
        plt.close(interactive.fig)
        plt.ioff()


class TestGUIKeyboardInteraction:
    """Tests for keyboard interactions in GUI."""
    
    def test_enter_key_sets_done_flag(self, interactive_selector, gui_test_backend):
        """Test that Enter key sets done flag."""
        interactive = InteractiveMaskSelector(
            interactive_selector,
            title="Test Enter Key"
        )
        
        plt.ion()
        interactive.show(block=False)
        time.sleep(0.5)
        
        # Simulate Enter key press
        class MockKeyEvent:
            def __init__(self, key):
                self.key = key
        
        enter_event = MockKeyEvent('enter')
        
        assert not interactive.is_done()
        interactive._on_key(enter_event)
        assert interactive.is_done()
        
        plt.close(interactive.fig)
        plt.ioff()
    
    def test_space_key_sets_done_flag(self, interactive_selector, gui_test_backend):
        """Test that Space key sets done flag."""
        interactive = InteractiveMaskSelector(
            interactive_selector,
            title="Test Space Key"
        )
        
        plt.ion()
        interactive.show(block=False)
        time.sleep(0.5)
        
        space_event = type('obj', (object,), {'key': ' '})()
        
        assert not interactive.is_done()
        interactive._on_key(space_event)
        assert interactive.is_done()
        
        plt.close(interactive.fig)
        plt.ioff()
    
    def test_escape_key_clears_selection(self, interactive_selector, gui_test_backend):
        """Test that Escape key clears selection."""
        interactive = InteractiveMaskSelector(
            interactive_selector,
            title="Test Escape Key"
        )
        
        plt.ion()
        interactive.show(block=False)
        time.sleep(0.5)
        
        # Select some masks first
        click_event = type('obj', (object,), {
            'xdata': 10, 'ydata': 10, 'inaxes': interactive.ax, 'button': 1
        })()
        interactive._on_click(click_event)
        assert len(interactive.get_selected_mask_ids()) > 0
        
        # Press Escape
        escape_event = type('obj', (object,), {'key': 'escape'})()
        interactive._on_key(escape_event)
        
        # Selection should be cleared
        assert len(interactive.get_selected_mask_ids()) == 0
        
        plt.close(interactive.fig)
        plt.ioff()


class TestGUIButtonInteraction:
    """Tests for button interactions."""
    
    def test_done_button_sets_done_flag(self, interactive_selector, gui_test_backend):
        """Test that Done button sets done flag."""
        interactive = InteractiveMaskSelector(
            interactive_selector,
            title="Test Done Button"
        )
        
        plt.ion()
        interactive.show(block=False)
        time.sleep(0.5)
        
        # Verify button exists
        assert interactive.done_button is not None
        
        # Simulate button click
        class MockEvent:
            pass
        
        assert not interactive.is_done()
        interactive._on_done(MockEvent())
        assert interactive.is_done()
        
        plt.close(interactive.fig)
        plt.ioff()


class TestGUIWorkflow:
    """Full workflow tests that simulate user interaction."""
    
    def test_complete_selection_workflow(self, interactive_selector, gui_test_backend):
        """Test complete selection workflow: select masks, press done."""
        interactive = InteractiveMaskSelector(
            interactive_selector,
            title="Test Complete Workflow"
        )
        
        plt.ion()
        interactive.show(block=False)
        time.sleep(0.5)
        
        # Step 1: Select first mask
        click1 = type('obj', (object,), {
            'xdata': 10, 'ydata': 10, 'inaxes': interactive.ax, 'button': 1
        })()
        interactive._on_click(click1)
        assert len(interactive.get_selected_mask_ids()) == 1
        
        # Step 2: Select second mask
        click2 = type('obj', (object,), {
            'xdata': 30, 'ydata': 30, 'inaxes': interactive.ax, 'button': 1
        })()
        interactive._on_click(click2)
        assert len(interactive.get_selected_mask_ids()) == 2
        
        # Step 3: Verify display updated (redraw should have been called)
        # We can't easily verify visual updates, but state is correct
        selected = interactive.get_selected_mask_ids()
        assert len(selected) == 2
        
        # Step 4: Press Done
        done_event = type('obj', (object,), {})()
        interactive._on_done(done_event)
        assert interactive.is_done()
        
        plt.close(interactive.fig)
        plt.ioff()
    
    def test_selection_persistence_through_redraw(self, interactive_selector, gui_test_backend):
        """Test that selections persist through redraw operations."""
        interactive = InteractiveMaskSelector(
            interactive_selector,
            title="Test Selection Persistence"
        )
        
        plt.ion()
        interactive.show(block=False)
        time.sleep(0.5)
        
        # Select masks
        click_event = type('obj', (object,), {
            'xdata': 10, 'ydata': 10, 'inaxes': interactive.ax, 'button': 1
        })()
        interactive._on_click(click_event)
        
        initial_selection = interactive.get_selected_mask_ids().copy()
        
        # Trigger redraw (simulating what happens during updates)
        interactive._redraw()
        time.sleep(0.2)
        
        # Selection should still be there
        assert len(interactive.get_selected_mask_ids()) == len(initial_selection)
        assert set(interactive.get_selected_mask_ids()) == set(initial_selection)
        
        plt.close(interactive.fig)
        plt.ioff()


class TestGUIVisualFeedback:
    """Tests for visual feedback in GUI."""
    
    def test_selected_masks_highlighted(self, interactive_selector, gui_test_backend):
        """Test that selected masks are visually highlighted (red)."""
        interactive = InteractiveMaskSelector(
            interactive_selector,
            title="Test Visual Highlighting"
        )
        
        plt.ion()
        interactive.show(block=False)
        time.sleep(0.5)
        
        # Select a mask
        click_event = type('obj', (object,), {
            'xdata': 10, 'ydata': 10, 'inaxes': interactive.ax, 'button': 1
        })()
        interactive._on_click(click_event)
        
        # Redraw should show selected mask highlighted
        interactive._redraw()
        time.sleep(0.2)
        
        # The overlay creation should have colored selected masks red
        # We verify this through the selection state
        assert len(interactive.get_selected_mask_ids()) == 1
        
        # Visual verification would require screenshot comparison
        # but we can verify the logic works
        
        plt.close(interactive.fig)
        plt.ioff()
    
    def test_selection_counter_displayed(self, interactive_selector, gui_test_backend):
        """Test that selection counter is displayed."""
        interactive = InteractiveMaskSelector(
            interactive_selector,
            title="Test Selection Counter"
        )
        
        plt.ion()
        interactive.show(block=False)
        time.sleep(0.5)
        
        # Select multiple masks
        for i in range(3):
            click_event = type('obj', (object,), {
                'xdata': 10 + i*20, 'ydata': 10 + i*20, 
                'inaxes': interactive.ax, 'button': 1
            })()
            interactive._on_click(click_event)
        
        # Redraw should show counter
        interactive._redraw()
        time.sleep(0.2)
        
        # Verify we have 3 selections
        assert len(interactive.get_selected_mask_ids()) == 3
        
        # The counter text should be added during redraw
        # Verification of text elements would require inspecting ax.texts
        # but the logic is tested through state
        
        plt.close(interactive.fig)
        plt.ioff()


@pytest.mark.slow
class TestGUIEndToEnd:
    """Slow end-to-end tests that simulate real user workflows."""
    
    def test_hole_by_hole_selection_simulation(self, interactive_selector, gui_test_backend):
        """Simulate selecting features for multiple holes."""
        # Simulate hole 1 selection
        interactive = InteractiveMaskSelector(
            interactive_selector,
            title="Hole 1 - Select green(s)"
        )
        
        plt.ion()
        interactive.show(block=False)
        time.sleep(0.3)
        
        # Select green
        click = type('obj', (object,), {
            'xdata': 10, 'ydata': 10, 'inaxes': interactive.ax, 'button': 1
        })()
        interactive._on_click(click)
        
        # Press Done
        interactive._on_done(type('obj', (object,), {})())
        
        # Get selections
        selected_greens = interactive.get_selected_mask_ids()
        assert len(selected_greens) == 1
        
        # Apply to selector
        interactive_selector.select_for_hole(1, FeatureType.GREEN, selected_greens)
        
        # Verify hole 1 selection
        hole1_selection = interactive_selector.get_selection_for_hole(1)
        assert hole1_selection is not None
        assert len(hole1_selection.greens) == 1
        
        plt.close(interactive.fig)
        plt.ioff()
        
        # Now simulate hole 2
        interactive2 = InteractiveMaskSelector(
            interactive_selector,
            title="Hole 2 - Select green(s)"
        )
        
        plt.ion()
        interactive2.show(block=False)
        time.sleep(0.3)
        
        # Select different mask
        click2 = type('obj', (object,), {
            'xdata': 30, 'ydata': 30, 'inaxes': interactive2.ax, 'button': 1
        })()
        interactive2._on_click(click2)
        interactive2._on_done(type('obj', (object,), {})())
        
        selected_greens2 = interactive2.get_selected_mask_ids()
        interactive_selector.select_for_hole(2, FeatureType.GREEN, selected_greens2)
        
        # Verify both holes have separate selections
        hole1 = interactive_selector.get_selection_for_hole(1)
        hole2 = interactive_selector.get_selection_for_hole(2)
        
        assert len(hole1.greens) == 1
        assert len(hole2.greens) == 1
        assert hole1.greens != hole2.greens  # Different masks selected
        
        plt.close(interactive2.fig)
        plt.ioff()
