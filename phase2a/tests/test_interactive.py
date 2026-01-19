"""
Tests for interactive selection module.
"""

import pytest
import numpy as np
from pathlib import Path
import json
import tempfile

from phase2a.pipeline.interactive import (
    InteractiveSelector,
    HoleSelection,
    FeatureType,
    SelectedMask,
)
from phase2a.pipeline.masks import MaskData


@pytest.fixture
def sample_masks():
    """Create sample masks for testing."""
    masks = []
    for i in range(5):
        # Create small masks at different positions
        mask = np.zeros((100, 100), dtype=bool)
        y_start = i * 15
        x_start = i * 15
        mask[y_start:y_start+10, x_start:x_start+10] = True
        
        mask_data = MaskData(
            id=f"mask_{i:04d}",
            mask=mask,
            area=100,
            bbox=(x_start, y_start, 10, 10),
            predicted_iou=0.9,
            stability_score=0.95,
        )
        masks.append(mask_data)
    
    return masks


@pytest.fixture
def sample_image():
    """Create a sample image."""
    return np.zeros((100, 100, 3), dtype=np.uint8)


class TestInteractiveSelector:
    """Tests for InteractiveSelector class."""
    
    def test_init(self, sample_masks, sample_image):
        """Test selector initialization."""
        selector = InteractiveSelector(sample_masks, sample_image)
        
        assert len(selector.masks) == 5
        assert selector.image.shape == (100, 100, 3)
        assert len(selector.selections) == 0
    
    def test_get_mask_at_point(self, sample_masks, sample_image):
        """Test finding mask at a point."""
        selector = InteractiveSelector(sample_masks, sample_image)
        
        # First mask should be at (0, 0) to (10, 10)
        mask_id = selector.get_mask_at_point(5, 5)
        assert mask_id == "mask_0000"
        
        # Second mask at (15, 15)
        mask_id = selector.get_mask_at_point(20, 20)
        assert mask_id == "mask_0001"
        
        # Point with no mask (use a point well outside all masks)
        # Masks are at: (0,0), (15,15), (30,30), (45,45), (60,60)
        # Use (90, 90) which is outside all masks
        mask_id = selector.get_mask_at_point(90, 90)
        assert mask_id is None
    
    def test_get_masks_in_region(self, sample_masks, sample_image):
        """Test finding masks in a region."""
        selector = InteractiveSelector(sample_masks, sample_image)
        
        # Region covering first two masks only
        # Masks are at: (0,0 to 10,10), (15,15 to 25,25), (30,30 to 40,40), ...
        # Use region (0, 0, 29, 29) which should only include first two
        mask_ids = selector.get_masks_in_region(0, 0, 29, 29)
        assert len(mask_ids) == 2
        assert "mask_0000" in mask_ids
        assert "mask_0001" in mask_ids
        
        # Region with no masks (well outside all masks)
        mask_ids = selector.get_masks_in_region(90, 90, 95, 95)
        assert len(mask_ids) == 0
    
    def test_select_for_hole(self, sample_masks, sample_image):
        """Test selecting masks for a hole."""
        selector = InteractiveSelector(sample_masks, sample_image)
        
        selector.select_for_hole(1, FeatureType.GREEN, ["mask_0000", "mask_0001"])
        
        selection = selector.get_selection_for_hole(1)
        assert selection is not None
        assert selection.hole == 1
        assert len(selection.greens) == 2
        assert "mask_0000" in selection.greens
        assert "mask_0001" in selection.greens
    
    def test_select_multiple_features(self, sample_masks, sample_image):
        """Test selecting multiple feature types for a hole."""
        selector = InteractiveSelector(sample_masks, sample_image)
        
        selector.select_for_hole(1, FeatureType.GREEN, ["mask_0000"])
        selector.select_for_hole(1, FeatureType.TEE, ["mask_0001"])
        selector.select_for_hole(1, FeatureType.FAIRWAY, ["mask_0002"])
        selector.select_for_hole(1, FeatureType.BUNKER, ["mask_0003"])
        
        selection = selector.get_selection_for_hole(1)
        assert len(selection.greens) == 1
        assert len(selection.tees) == 1
        assert len(selection.fairways) == 1
        assert len(selection.bunkers) == 1
    
    def test_select_removes_duplicates(self, sample_masks, sample_image):
        """Test that duplicate selections are removed."""
        selector = InteractiveSelector(sample_masks, sample_image)
        
        # Add same mask twice
        selector.select_for_hole(1, FeatureType.GREEN, ["mask_0000", "mask_0000"])
        
        selection = selector.get_selection_for_hole(1)
        assert len(selection.greens) == 1
    
    def test_save_and_load_selections(self, sample_masks, sample_image, temp_dir):
        """Test saving and loading selections."""
        selector = InteractiveSelector(sample_masks, sample_image)
        
        selector.select_for_hole(1, FeatureType.GREEN, ["mask_0000"])
        selector.select_for_hole(2, FeatureType.TEE, ["mask_0001"])
        
        # Save
        selections_path = temp_dir / "selections.json"
        selector.save_selections(selections_path)
        assert selections_path.exists()
        
        # Load
        loaded = InteractiveSelector.load_selections(selections_path)
        assert 1 in loaded
        assert 2 in loaded
        assert loaded[1].greens == ["mask_0000"]
        assert loaded[2].tees == ["mask_0001"]


class TestHoleSelection:
    """Tests for HoleSelection dataclass."""
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        selection = HoleSelection(
            hole=1,
            greens=["mask_0000"],
            tees=["mask_0001"],
        )
        
        data = selection.to_dict()
        assert data["hole"] == 1
        assert data["greens"] == ["mask_0000"]
        assert data["tees"] == ["mask_0001"]
    
    def test_from_dict(self):
        """Test loading from dictionary."""
        data = {
            "hole": 2,
            "greens": ["mask_0000", "mask_0001"],
            "tees": [],
            "fairways": [],
            "bunkers": [],
            "water": [],
            "rough": [],
        }
        
        selection = HoleSelection.from_dict(data)
        assert selection.hole == 2
        assert len(selection.greens) == 2


class TestFeatureType:
    """Tests for FeatureType enum."""
    
    def test_feature_types(self):
        """Test all feature types exist."""
        assert FeatureType.GREEN == "green"
        assert FeatureType.TEE == "tee"
        assert FeatureType.FAIRWAY == "fairway"
        assert FeatureType.BUNKER == "bunker"
        assert FeatureType.WATER == "water"
        assert FeatureType.ROUGH == "rough"


class TestInteractiveVisualization:
    """Tests for interactive visualization (using non-interactive backend)."""
    
    @pytest.fixture(autouse=True)
    def setup_matplotlib_backend(self):
        """Set matplotlib to non-interactive backend for testing."""
        try:
            import matplotlib
            matplotlib.use('Agg')  # Non-interactive backend (no GUI needed)
        except ImportError:
            pytest.skip("matplotlib not available")
    
    def test_interactive_selector_initialization(self, sample_masks, sample_image):
        """Test InteractiveMaskSelector can be initialized."""
        try:
            from phase2a.pipeline.visualize import InteractiveMaskSelector
            
            selector = InteractiveSelector(sample_masks, sample_image)
            interactive = InteractiveMaskSelector(selector, "Test Title")
            
            assert interactive.selector == selector
            assert interactive.title == "Test Title"
            assert len(interactive.selected_mask_ids) == 0
            assert not interactive.is_done()
        except ImportError:
            pytest.skip("matplotlib not available")
    
    def test_selection_tracking(self, sample_masks, sample_image):
        """Test that selections can be tracked without GUI."""
        try:
            from phase2a.pipeline.visualize import InteractiveMaskSelector
            
            selector = InteractiveSelector(sample_masks, sample_image)
            interactive = InteractiveMaskSelector(selector, "Test")
            
            # Simulate selections
            interactive.selected_mask_ids = ["mask_0000", "mask_0001"]
            
            assert len(interactive.get_selected_mask_ids()) == 2
            assert "mask_0000" in interactive.get_selected_mask_ids()
            assert "mask_0001" in interactive.get_selected_mask_ids()
        except ImportError:
            pytest.skip("matplotlib not available")
    
    def test_clear_selection(self, sample_masks, sample_image):
        """Test clearing selections."""
        try:
            from phase2a.pipeline.visualize import InteractiveMaskSelector
            
            selector = InteractiveSelector(sample_masks, sample_image)
            interactive = InteractiveMaskSelector(selector, "Test")
            
            interactive.selected_mask_ids = ["mask_0000", "mask_0001"]
            interactive.clear_selection()
            
            assert len(interactive.get_selected_mask_ids()) == 0
        except ImportError:
            pytest.skip("matplotlib not available")
    
    def test_mask_overlay_creation(self, sample_masks, sample_image):
        """Test mask overlay creation (logic only, no GUI)."""
        try:
            from phase2a.pipeline.visualize import create_mask_overlay
            
            selected_ids = ["mask_0000"]
            overlay = create_mask_overlay(sample_image, sample_masks, selected_ids)
            
            assert overlay.shape == sample_image.shape
            assert overlay.dtype == np.uint8
            # Selected mask should have red tint, unselected should have yellow
        except ImportError:
            pytest.skip("matplotlib/PIL not available")
    
    def test_mask_overlay_with_no_selection(self, sample_masks, sample_image):
        """Test overlay creation with no selected masks."""
        try:
            from phase2a.pipeline.visualize import create_mask_overlay
            
            overlay = create_mask_overlay(sample_image, sample_masks, None)
            
            assert overlay.shape == sample_image.shape
            assert overlay.dtype == np.uint8
        except ImportError:
            pytest.skip("matplotlib/PIL not available")
    
    def test_done_flag(self, sample_masks, sample_image):
        """Test done flag handling."""
        try:
            from phase2a.pipeline.visualize import InteractiveMaskSelector
            
            selector = InteractiveSelector(sample_masks, sample_image)
            interactive = InteractiveMaskSelector(selector, "Test")
            
            assert not interactive.is_done()
            
            # Simulate done press
            interactive._on_done(None)
            
            assert interactive.is_done()
            
            # Reset
            interactive.reset_done()
            assert not interactive.is_done()
        except ImportError:
            pytest.skip("matplotlib not available")
    
    def test_keyboard_events(self, sample_masks, sample_image):
        """Test keyboard event handling (mocked)."""
        try:
            from phase2a.pipeline.visualize import InteractiveMaskSelector
            
            selector = InteractiveSelector(sample_masks, sample_image)
            interactive = InteractiveMaskSelector(selector, "Test")
            
            # Mock keyboard events
            class MockKeyEvent:
                def __init__(self, key):
                    self.key = key
            
            # Test Enter key
            interactive._on_key(MockKeyEvent('enter'))
            assert interactive.is_done()
            
            interactive.reset_done()
            
            # Test Space key
            interactive._on_key(MockKeyEvent(' '))
            assert interactive.is_done()
            
            interactive.reset_done()
            
            # Test Escape key (should clear selection)
            interactive.selected_mask_ids = ["mask_0000", "mask_0001"]
            interactive._on_key(MockKeyEvent('escape'))
            assert len(interactive.get_selected_mask_ids()) == 0
        except ImportError:
            pytest.skip("matplotlib not available")
    
    def test_click_event_handler(self, sample_masks, sample_image):
        """Test click event handling logic (without actual GUI)."""
        try:
            from phase2a.pipeline.visualize import InteractiveMaskSelector
            
            selector = InteractiveSelector(sample_masks, sample_image)
            interactive = InteractiveMaskSelector(selector, "Test")
            
            # Initialize figure and axes (needed for click handler)
            import matplotlib.pyplot as plt
            interactive.fig, interactive.ax = plt.subplots(figsize=(8, 6))
            
            # Mock click event on first mask (at position 5, 5)
            class MockClickEvent:
                def __init__(self, x, y):
                    self.xdata = x
                    self.ydata = y
                    self.inaxes = interactive.ax
                    self.button = 1  # Left button
            
            # Click on first mask
            event = MockClickEvent(5, 5)
            interactive._on_click(event)
            
            assert len(interactive.get_selected_mask_ids()) == 1
            assert "mask_0000" in interactive.get_selected_mask_ids()
            
            # Click again to deselect
            interactive._on_click(event)
            assert len(interactive.get_selected_mask_ids()) == 0
            
            # Click on position with no mask (well outside all masks)
            # Masks are at: (0-9), (15-24), (30-39), (45-54), (60-69)
            # Use (90, 90) which is outside all masks
            event_no_mask = MockClickEvent(90, 90)
            initial_count = len(interactive.get_selected_mask_ids())
            interactive._on_click(event_no_mask)
            assert len(interactive.get_selected_mask_ids()) == initial_count
            
            plt.close(interactive.fig)
        except ImportError:
            pytest.skip("matplotlib not available")


class TestInteractiveSelectorIntegration:
    """Integration tests for interactive selection workflow."""
    
    def test_hole_by_hole_selection_workflow(self, sample_masks, sample_image):
        """Test complete hole-by-hole selection workflow."""
        selector = InteractiveSelector(sample_masks, sample_image)
        
        # Simulate selecting features for hole 1
        selector.select_for_hole(1, FeatureType.GREEN, ["mask_0000"])
        selector.select_for_hole(1, FeatureType.TEE, ["mask_0001"])
        selector.select_for_hole(1, FeatureType.FAIRWAY, ["mask_0002"])
        selector.select_for_hole(1, FeatureType.BUNKER, ["mask_0003"])
        
        # Verify selections
        selection = selector.get_selection_for_hole(1)
        assert selection is not None
        assert len(selection.greens) == 1
        assert len(selection.tees) == 1
        assert len(selection.fairways) == 1
        assert len(selection.bunkers) == 1
        
        # Simulate selecting features for hole 2
        selector.select_for_hole(2, FeatureType.GREEN, ["mask_0004"])
        
        selection2 = selector.get_selection_for_hole(2)
        assert selection2 is not None
        assert len(selection2.greens) == 1
        
        # Verify both holes are separate
        assert len(selector.get_all_selections()) == 2
    
    def test_invalid_mask_ids_ignored(self, sample_masks, sample_image):
        """Test that invalid mask IDs are ignored."""
        selector = InteractiveSelector(sample_masks, sample_image)
        
        # Mix valid and invalid IDs
        selector.select_for_hole(1, FeatureType.GREEN, ["mask_0000", "invalid_mask", "mask_0001"])
        
        selection = selector.get_selection_for_hole(1)
        assert len(selection.greens) == 2
        assert "invalid_mask" not in selection.greens
    
    def test_mask_summary(self, sample_masks, sample_image):
        """Test getting mask summary."""
        selector = InteractiveSelector(sample_masks, sample_image)
        
        summary = selector.get_mask_summary()
        
        assert len(summary) == 5
        assert "mask_0000" in summary
        assert "centroid" in summary["mask_0000"]
        assert "area" in summary["mask_0000"]
        assert "bbox" in summary["mask_0000"]


class TestPointBasedSelectorIntegration:
    """Integration tests connecting point-based selection with interactive workflow."""
    
    def test_point_based_selector_import(self):
        """Test that PointBasedSelector can be imported."""
        from phase2a.pipeline.point_selector import PointBasedSelector
        assert PointBasedSelector is not None
    
    def test_point_based_workflow_with_mock(self, sample_image):
        """Test point-based workflow with mocked SAM."""
        from phase2a.pipeline.point_selector import PointBasedSelector
        from phase2a.pipeline.interactive import FeatureType
        from unittest.mock import Mock
        from phase2a.pipeline.masks import MaskData
        
        # Create mock generator
        mock_generator = Mock()
        
        # Create a test mask
        test_mask = np.zeros((200, 200), dtype=bool)
        test_mask[70:90, 70:90] = True
        
        def mock_generate(image, point, label=1):
            return MaskData(
                id="test",
                mask=test_mask,
                area=400,
                bbox=(70, 70, 20, 20),
                predicted_iou=0.9,
                stability_score=0.95,
            )
        
        mock_generator.generate_from_point = Mock(side_effect=mock_generate)
        
        selector = PointBasedSelector(sample_image, mock_generator)
        
        # Test clicking
        mask = selector.click_to_mask(75, 75, hole=1, feature_type=FeatureType.GREEN)
        
        assert mask is not None
        assert len(selector.generated_masks) == 1
        assert len(selector.get_selection_for_hole(1).greens) == 1
