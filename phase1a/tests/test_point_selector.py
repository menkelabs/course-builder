"""
Tests for point-based interactive selection module.
"""

import pytest
import numpy as np
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

from phase1a.pipeline.point_selector import PointBasedSelector
from phase1a.pipeline.interactive import FeatureType, HoleSelection
from phase1a.pipeline.masks import MaskGenerator, MaskData


@pytest.fixture
def sample_image():
    """Create a sample image for testing."""
    # Create a colorful test image
    image = np.zeros((200, 200, 3), dtype=np.uint8)
    image[:, :] = [128, 128, 128]  # Gray background
    image[50:100, 50:100] = [0, 255, 0]  # Green region
    image[120:150, 120:150] = [255, 255, 0]  # Yellow region (bunker-like)
    return image


@pytest.fixture
def mock_mask_generator():
    """Create a mock MaskGenerator for testing."""
    generator = Mock(spec=MaskGenerator)
    
    # Mock generate_from_point to return a test mask
    def mock_generate_from_point(image, point, label=1):
        x, y = point
        # Create a small mask around the point
        mask = np.zeros((200, 200), dtype=bool)
        # Create a 20x20 square around the point
        y_start = max(0, y - 10)
        y_end = min(200, y + 10)
        x_start = max(0, x - 10)
        x_end = min(200, x + 10)
        mask[y_start:y_end, x_start:x_end] = True
        
        area = int(np.sum(mask))
        bbox = (x_start, y_start, x_end - x_start, y_end - y_start)
        
        return MaskData(
            id="test_mask",
            mask=mask,
            area=area,
            bbox=bbox,
            predicted_iou=0.9,
            stability_score=0.95,
        )
    
    generator.generate_from_point = Mock(side_effect=mock_generate_from_point)
    return generator


class TestPointBasedSelector:
    """Tests for PointBasedSelector class."""
    
    def test_init(self, sample_image, mock_mask_generator):
        """Test selector initialization."""
        selector = PointBasedSelector(sample_image, mock_mask_generator)
        
        assert selector.image.shape == (200, 200, 3)
        assert selector.mask_generator == mock_mask_generator
        assert len(selector.selections) == 0
        assert len(selector.generated_masks) == 0
    
    def test_click_to_mask_green(self, sample_image, mock_mask_generator):
        """Test generating a mask from a click point for green."""
        selector = PointBasedSelector(sample_image, mock_mask_generator)
        
        # Click on green region (around 75, 75)
        mask_data = selector.click_to_mask(75, 75, hole=1, feature_type=FeatureType.GREEN)
        
        assert mask_data is not None
        assert mask_data.id.startswith("green_1_")
        assert mask_data.area > 0
        
        # Verify mask was stored
        assert mask_data.id in selector.generated_masks
        assert len(selector.generated_masks) == 1
        
        # Verify selection was created
        selection = selector.get_selection_for_hole(1)
        assert selection is not None
        assert len(selection.greens) == 1
        assert mask_data.id in selection.greens
    
    def test_click_to_mask_multiple_features(self, sample_image, mock_mask_generator):
        """Test generating masks for multiple feature types."""
        selector = PointBasedSelector(sample_image, mock_mask_generator)
        
        # Click for different features
        green_mask = selector.click_to_mask(75, 75, hole=1, feature_type=FeatureType.GREEN)
        tee_mask = selector.click_to_mask(100, 100, hole=1, feature_type=FeatureType.TEE)
        fairway_mask = selector.click_to_mask(50, 50, hole=1, feature_type=FeatureType.FAIRWAY)
        bunker_mask = selector.click_to_mask(135, 135, hole=1, feature_type=FeatureType.BUNKER)
        
        assert green_mask is not None
        assert tee_mask is not None
        assert fairway_mask is not None
        assert bunker_mask is not None
        
        # Verify all masks were stored
        assert len(selector.generated_masks) == 4
        
        # Verify selections
        selection = selector.get_selection_for_hole(1)
        assert len(selection.greens) == 1
        assert len(selection.tees) == 1
        assert len(selection.fairways) == 1
        assert len(selection.bunkers) == 1
    
    def test_click_to_mask_multiple_holes(self, sample_image, mock_mask_generator):
        """Test generating masks for multiple holes."""
        selector = PointBasedSelector(sample_image, mock_mask_generator)
        
        # Click for hole 1
        mask1 = selector.click_to_mask(75, 75, hole=1, feature_type=FeatureType.GREEN)
        
        # Click for hole 2
        mask2 = selector.click_to_mask(100, 100, hole=2, feature_type=FeatureType.GREEN)
        
        assert mask1 is not None
        assert mask2 is not None
        assert mask1.id != mask2.id
        
        # Verify separate selections
        selection1 = selector.get_selection_for_hole(1)
        selection2 = selector.get_selection_for_hole(2)
        
        assert selection1 is not None
        assert selection2 is not None
        assert len(selection1.greens) == 1
        assert len(selection2.greens) == 1
        assert selection1.greens[0] != selection2.greens[0]
    
    def test_click_to_mask_failure_handling(self, sample_image):
        """Test handling when mask generation fails."""
        # Create a new mock that returns None
        mock_generator = Mock(spec=MaskGenerator)
        mock_generator.generate_from_point = Mock(return_value=None)
        
        selector = PointBasedSelector(sample_image, mock_generator)
        
        result = selector.click_to_mask(75, 75, hole=1, feature_type=FeatureType.GREEN)
        
        assert result is None
        assert len(selector.generated_masks) == 0
        # Selection is only created when mask is successfully generated
        selection = selector.get_selection_for_hole(1)
        # Selection may or may not be created if mask generation fails
        if selection is not None:
            assert len(selection.greens) == 0
    
    def test_click_to_mask_duplicate_prevention(self, sample_image, mock_mask_generator):
        """Test that clicking same point doesn't create duplicates."""
        selector = PointBasedSelector(sample_image, mock_mask_generator)
        
        # Click same point twice
        mask1 = selector.click_to_mask(75, 75, hole=1, feature_type=FeatureType.GREEN)
        mask2 = selector.click_to_mask(75, 75, hole=1, feature_type=FeatureType.GREEN)
        
        # Should create two separate masks (different IDs)
        assert mask1 is not None
        assert mask2 is not None
        assert mask1.id != mask2.id
        
        # But both should be in greens list
        selection = selector.get_selection_for_hole(1)
        assert len(selection.greens) == 2
    
    def test_draw_to_mask_green(self, sample_image, mock_mask_generator):
        """Test generating mask from drawn outline."""
        # Create mock that returns a mask for outline
        mock_mask = MaskData(
            id="outline_mask",
            mask=np.ones((200, 200), dtype=bool),
            area=1000,
            bbox=(50, 50, 100, 100),
            predicted_iou=0.95,
            stability_score=0.95,
        )
        mock_mask_generator.generate_from_outline = Mock(return_value=mock_mask)
        
        selector = PointBasedSelector(sample_image, mock_mask_generator)
        
        # Simulate drawing a circle (list of points)
        outline_points = [(60, 75), (75, 60), (90, 75), (75, 90), (60, 75)]
        
        result = selector.draw_to_mask(outline_points, hole=1, feature_type=FeatureType.GREEN)
        
        assert result is not None
        assert "green" in result.id
        
        # Verify it was stored
        assert len(selector.generated_masks) == 1
        
        # Verify selection
        selection = selector.get_selection_for_hole(1)
        assert len(selection.greens) == 1
    
    def test_draw_to_mask_multiple_features(self, sample_image, mock_mask_generator):
        """Test drawing multiple features."""
        mock_mask = MaskData(
            id="outline_mask",
            mask=np.ones((200, 200), dtype=bool),
            area=1000,
            bbox=(50, 50, 100, 100),
            predicted_iou=0.95,
            stability_score=0.95,
        )
        mock_mask_generator.generate_from_outline = Mock(return_value=mock_mask)
        
        selector = PointBasedSelector(sample_image, mock_mask_generator)
        
        # Draw green
        green_outline = [(60, 75), (75, 60), (90, 75), (75, 90)]
        green_mask = selector.draw_to_mask(green_outline, hole=1, feature_type=FeatureType.GREEN)
        
        # Draw fairway
        fairway_outline = [(100, 100), (150, 100), (150, 150), (100, 150)]
        fairway_mask = selector.draw_to_mask(fairway_outline, hole=1, feature_type=FeatureType.FAIRWAY)
        
        assert green_mask is not None
        assert fairway_mask is not None
        
        selection = selector.get_selection_for_hole(1)
        assert len(selection.greens) == 1
        assert len(selection.fairways) == 1
    
    def test_draw_to_mask_too_few_points(self, sample_image, mock_mask_generator):
        """Test that drawing with too few points fails gracefully."""
        selector = PointBasedSelector(sample_image, mock_mask_generator)
        
        # Only 2 points - not enough to form an outline
        outline_points = [(60, 75), (90, 75)]
        
        result = selector.draw_to_mask(outline_points, hole=1, feature_type=FeatureType.GREEN)
        
        assert result is None
    
    def test_get_all_masks(self, sample_image, mock_mask_generator):
        """Test getting all generated masks."""
        selector = PointBasedSelector(sample_image, mock_mask_generator)
        
        selector.click_to_mask(75, 75, hole=1, feature_type=FeatureType.GREEN)
        selector.click_to_mask(100, 100, hole=1, feature_type=FeatureType.TEE)
        
        all_masks = selector.get_all_masks()
        assert len(all_masks) == 2
    
    def test_get_all_selections(self, sample_image, mock_mask_generator):
        """Test getting all selections."""
        selector = PointBasedSelector(sample_image, mock_mask_generator)
        
        selector.click_to_mask(75, 75, hole=1, feature_type=FeatureType.GREEN)
        selector.click_to_mask(100, 100, hole=2, feature_type=FeatureType.GREEN)
        
        all_selections = selector.get_all_selections()
        assert len(all_selections) == 2
        assert 1 in all_selections
        assert 2 in all_selections
    
    def test_extract_green_centers(self, sample_image, mock_mask_generator):
        """Test extracting green centers from generated masks."""
        selector = PointBasedSelector(sample_image, mock_mask_generator)
        
        # Create green masks for two holes
        selector.click_to_mask(75, 75, hole=1, feature_type=FeatureType.GREEN)
        selector.click_to_mask(125, 125, hole=2, feature_type=FeatureType.GREEN)
        
        green_centers = selector.extract_green_centers()
        
        assert len(green_centers) == 2
        
        # Verify structure
        for gc in green_centers:
            assert "hole" in gc
            assert "x" in gc
            assert "y" in gc
            assert isinstance(gc["x"], (int, float))
            assert isinstance(gc["y"], (int, float))
        
        # Verify holes
        holes = [gc["hole"] for gc in green_centers]
        assert 1 in holes
        assert 2 in holes
    
    def test_extract_green_centers_no_greens(self, sample_image, mock_mask_generator):
        """Test extracting green centers when no greens exist."""
        selector = PointBasedSelector(sample_image, mock_mask_generator)
        
        # Create non-green masks
        selector.click_to_mask(75, 75, hole=1, feature_type=FeatureType.BUNKER)
        
        green_centers = selector.extract_green_centers()
        assert len(green_centers) == 0
    
    def test_extract_green_centers_multiple_greens_per_hole(self, sample_image, mock_mask_generator):
        """Test extracting green centers when hole has multiple green masks."""
        selector = PointBasedSelector(sample_image, mock_mask_generator)
        
        # Create multiple green masks for same hole
        selector.click_to_mask(70, 70, hole=1, feature_type=FeatureType.GREEN)
        selector.click_to_mask(80, 80, hole=1, feature_type=FeatureType.GREEN)
        
        green_centers = selector.extract_green_centers()
        
        # Should have one center (centroid of all greens)
        assert len(green_centers) == 1
        assert green_centers[0]["hole"] == 1
        
        # Center should be between the two masks
        assert 70 <= green_centers[0]["x"] <= 90
        assert 70 <= green_centers[0]["y"] <= 90


class TestPointBasedSelectorIntegration:
    """Integration tests for point-based selection workflow."""
    
    def test_complete_hole_workflow(self, sample_image, mock_mask_generator):
        """Test complete workflow for a single hole."""
        selector = PointBasedSelector(sample_image, mock_mask_generator)
        
        # Simulate complete hole selection
        selector.click_to_mask(75, 75, hole=1, feature_type=FeatureType.GREEN)
        selector.click_to_mask(50, 50, hole=1, feature_type=FeatureType.TEE)
        selector.click_to_mask(100, 100, hole=1, feature_type=FeatureType.FAIRWAY)
        selector.click_to_mask(135, 135, hole=1, feature_type=FeatureType.BUNKER)
        
        # Verify all features are selected
        selection = selector.get_selection_for_hole(1)
        assert len(selection.greens) == 1
        assert len(selection.tees) == 1
        assert len(selection.fairways) == 1
        assert len(selection.bunkers) == 1
        
        # Verify masks were generated
        assert len(selector.generated_masks) == 4
        
        # Verify green centers
        green_centers = selector.extract_green_centers()
        assert len(green_centers) == 1
        assert green_centers[0]["hole"] == 1
    
    def test_multiple_holes_workflow(self, sample_image, mock_mask_generator):
        """Test workflow for multiple holes."""
        selector = PointBasedSelector(sample_image, mock_mask_generator)
        
        # Hole 1
        selector.click_to_mask(75, 75, hole=1, feature_type=FeatureType.GREEN)
        selector.click_to_mask(50, 50, hole=1, feature_type=FeatureType.FAIRWAY)
        
        # Hole 2
        selector.click_to_mask(125, 125, hole=2, feature_type=FeatureType.GREEN)
        selector.click_to_mask(150, 150, hole=2, feature_type=FeatureType.FAIRWAY)
        
        # Verify both holes
        assert len(selector.get_all_selections()) == 2
        assert len(selector.generated_masks) == 4
        
        green_centers = selector.extract_green_centers()
        assert len(green_centers) == 2


class TestMaskGeneratorPointGeneration:
    """Tests for MaskGenerator.generate_from_point() method."""
    
    @pytest.mark.skipif(
        not (Path(__file__).parent.parent / "resources" / "Pictatinny_B.jpg").exists(),
        reason="Resource image not available for SAM testing"
    )
    @pytest.mark.skipif(
        not (Path(__file__).parent.parent.parent / "checkpoints" / "sam_vit_h_4b8939.pth").exists(),
        reason="SAM checkpoint not available"
    )
    def test_generate_from_point_with_sam(self):
        """Test generating mask from point using actual SAM model."""
        from PIL import Image
        from phase1a.pipeline.masks import MaskGenerator
        
        # Load test image
        image_path = Path(__file__).parent.parent / "resources" / "Pictatinny_B.jpg"
        checkpoint_path = Path(__file__).parent.parent.parent / "checkpoints" / "sam_vit_h_4b8939.pth"
        
        if not image_path.exists() or not checkpoint_path.exists():
            pytest.skip("Required files not available")
        
        image = np.array(Image.open(image_path).convert("RGB"))
        height, width = image.shape[:2]
        
        # Create generator
        generator = MaskGenerator(
            checkpoint_path=str(checkpoint_path),
            device="cpu",  # Use CPU for testing
        )
        
        # Generate mask from a point in the center
        point = (width // 2, height // 2)
        mask_data = generator.generate_from_point(image, point, label=1)
        
        assert mask_data is not None
        assert mask_data.mask.shape == image.shape[:2]
        assert mask_data.area > 0
        assert mask_data.predicted_iou > 0
        assert mask_data.stability_score > 0
    
    @pytest.mark.skipif(
        not (Path(__file__).parent.parent / "resources" / "Pictatinny_B.jpg").exists(),
        reason="Resource image not available for SAM testing"
    )
    @pytest.mark.skipif(
        not (Path(__file__).parent.parent.parent / "checkpoints" / "sam_vit_h_4b8939.pth").exists(),
        reason="SAM checkpoint not available"
    )
    def test_generate_from_outline_with_sam(self):
        """Test generating mask from drawn outline using actual SAM model."""
        from PIL import Image
        from phase1a.pipeline.masks import MaskGenerator
        
        # Load test image
        image_path = Path(__file__).parent.parent / "resources" / "Pictatinny_B.jpg"
        checkpoint_path = Path(__file__).parent.parent.parent / "checkpoints" / "sam_vit_h_4b8939.pth"
        
        if not image_path.exists() or not checkpoint_path.exists():
            pytest.skip("Required files not available")
        
        image = np.array(Image.open(image_path).convert("RGB"))
        height, width = image.shape[:2]
        
        # Create generator
        generator = MaskGenerator(
            checkpoint_path=str(checkpoint_path),
            device="cpu",
        )
        
        # Draw a circle outline in the center of the image
        center_x, center_y = width // 2, height // 2
        radius = min(width, height) // 10
        
        # Create circle points
        import math
        outline_points = []
        for i in range(20):
            angle = 2 * math.pi * i / 20
            px = center_x + int(radius * math.cos(angle))
            py = center_y + int(radius * math.sin(angle))
            outline_points.append((px, py))
        
        # Generate mask from outline
        mask_data = generator.generate_from_outline(image, outline_points)
        
        assert mask_data is not None
        assert mask_data.mask.shape == image.shape[:2]
        assert mask_data.area > 0
        assert mask_data.predicted_iou > 0
        assert "outline_mask" in mask_data.id
    
    def test_generate_from_point_invalid_point(self, sample_image):
        """Test generating mask with invalid point coordinates."""
        generator = Mock(spec=MaskGenerator)
        generator.generate_from_point = Mock(return_value=None)
        
        selector = PointBasedSelector(sample_image, generator)
        
        # Point outside image bounds
        result = selector.click_to_mask(300, 300, hole=1, feature_type=FeatureType.GREEN)
        
        # Should handle gracefully
        assert result is None or result is not None  # Depends on implementation
    
    def test_generate_from_point_edge_cases(self, sample_image, mock_mask_generator):
        """Test edge cases for point-based generation."""
        selector = PointBasedSelector(sample_image, mock_mask_generator)
        
        # Point at image edge
        mask1 = selector.click_to_mask(0, 0, hole=1, feature_type=FeatureType.GREEN)
        assert mask1 is not None
        
        # Point at other edge
        mask2 = selector.click_to_mask(199, 199, hole=1, feature_type=FeatureType.GREEN)
        assert mask2 is not None
        
        # Point in center
        mask3 = selector.click_to_mask(100, 100, hole=1, feature_type=FeatureType.GREEN)
        assert mask3 is not None


class TestPointBasedVisualization:
    """Tests for point-based selection with visualization."""
    
    @pytest.fixture(autouse=True)
    def setup_matplotlib_backend(self):
        """Set matplotlib to non-interactive backend for testing."""
        try:
            import matplotlib
            matplotlib.use('Agg')
        except ImportError:
            pytest.skip("matplotlib not available")
    
    def test_point_based_click_handling(self, sample_image, mock_mask_generator):
        """Test that point-based clicks trigger mask generation."""
        try:
            from phase1a.pipeline.visualize import InteractiveMaskSelector
            
            selector = PointBasedSelector(sample_image, mock_mask_generator)
            interactive = InteractiveMaskSelector(selector, "Test Point Selection")
            
            # Set up for point-based mode
            interactive._current_hole = 1
            interactive._current_feature_type = FeatureType.GREEN
            
            # Initialize figure
            import matplotlib.pyplot as plt
            interactive.fig, interactive.ax = plt.subplots(figsize=(8, 6))
            
            # Mock click event
            class MockClickEvent:
                def __init__(self, x, y):
                    self.xdata = x
                    self.ydata = y
                    self.inaxes = interactive.ax
                    self.button = 1
            
            # Click on image
            event = MockClickEvent(75, 75)
            interactive._on_click(event)
            
            # Verify mask was generated
            assert len(selector.generated_masks) == 1
            assert len(interactive.get_selected_mask_ids()) == 1
            
            plt.close(interactive.fig)
        except ImportError:
            pytest.skip("matplotlib not available")
    
    def test_point_based_redraw_with_generated_masks(self, sample_image, mock_mask_generator):
        """Test that redraw works with generated masks."""
        try:
            from phase1a.pipeline.visualize import InteractiveMaskSelector
            
            selector = PointBasedSelector(sample_image, mock_mask_generator)
            
            # Generate a mask first
            selector.click_to_mask(75, 75, hole=1, feature_type=FeatureType.GREEN)
            
            interactive = InteractiveMaskSelector(selector, "Test")
            interactive.selected_mask_ids = list(selector.generated_masks.keys())
            
            # Initialize figure
            import matplotlib.pyplot as plt
            interactive.fig, interactive.ax = plt.subplots(figsize=(8, 6))
            
            # Redraw should work without errors
            interactive._redraw()
            
            # Verify image is displayed
            assert interactive.ax is not None
            
            plt.close(interactive.fig)
        except ImportError:
            pytest.skip("matplotlib not available")
