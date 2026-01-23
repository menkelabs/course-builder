"""
Tests for mask merging and filled polygon functionality.

These features support the SAM mask completion workflow where:
1. User generates a SAM mask that doesn't fully cover an area
2. User draws a filled polygon to cover the missing area
3. User merges both masks with smooth edges
"""

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock

from phase2a.pipeline.masks import MaskGenerator, MaskData, merge_masks
from phase2a.pipeline.point_selector import PointBasedSelector
from phase2a.pipeline.interactive import FeatureType


@pytest.fixture
def sample_image():
    """Create a sample image for testing."""
    image = np.zeros((200, 200, 3), dtype=np.uint8)
    image[:, :] = [100, 150, 100]  # Green-ish background
    return image


@pytest.fixture
def sample_mask_1():
    """Create first sample mask (e.g., SAM-generated, incomplete)."""
    mask = np.zeros((200, 200), dtype=bool)
    # Left portion of an area
    mask[50:100, 30:80] = True
    return MaskData(
        id="sam_mask_001",
        mask=mask,
        area=int(np.sum(mask)),
        bbox=(30, 50, 50, 50),
        predicted_iou=0.92,
        stability_score=0.95,
    )


@pytest.fixture
def sample_mask_2():
    """Create second sample mask (e.g., manually drawn to fill gap)."""
    mask = np.zeros((200, 200), dtype=bool)
    # Right portion that fills the gap
    mask[50:100, 70:120] = True
    return MaskData(
        id="filled_polygon_001",
        mask=mask,
        area=int(np.sum(mask)),
        bbox=(70, 50, 50, 50),
        predicted_iou=1.0,
        stability_score=1.0,
    )


@pytest.fixture
def mock_mask_generator():
    """Create a mock MaskGenerator."""
    generator = Mock(spec=MaskGenerator)
    generator.min_mask_region_area = 100
    
    def mock_generate_filled_polygon(image, outline_points, smooth_edges=True):
        xs = [int(p[0]) for p in outline_points]
        ys = [int(p[1]) for p in outline_points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        
        mask = np.zeros((200, 200), dtype=bool)
        mask[min_y:max_y, min_x:max_x] = True
        
        return MaskData(
            id=f"filled_polygon_{min_x}_{min_y}",
            mask=mask,
            area=int(np.sum(mask)),
            bbox=(min_x, min_y, max_x - min_x, max_y - min_y),
            predicted_iou=1.0,
            stability_score=1.0,
        )
    
    generator.generate_filled_polygon = Mock(side_effect=mock_generate_filled_polygon)
    
    def mock_generate_from_outline(image, outline_points, color_tolerance=6.0):
        xs = [int(p[0]) for p in outline_points]
        ys = [int(p[1]) for p in outline_points]
        center_x = int(np.mean(xs))
        center_y = int(np.mean(ys))
        
        mask = np.zeros((200, 200), dtype=bool)
        mask[min(ys):max(ys), min(xs):max(xs)] = True
        
        return MaskData(
            id=f"outline_mask_{center_x}_{center_y}",
            mask=mask,
            area=int(np.sum(mask)),
            bbox=(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)),
            predicted_iou=0.9,
            stability_score=0.9,
        )
    
    generator.generate_from_outline = Mock(side_effect=mock_generate_from_outline)
    
    return generator


class TestMergeMasks:
    """Tests for the merge_masks() function."""
    
    def test_merge_two_masks(self, sample_mask_1, sample_mask_2):
        """Test merging two overlapping masks."""
        merged = merge_masks([sample_mask_1, sample_mask_2])
        
        assert merged is not None
        assert "merged" in merged.id
        
        # Merged area should be >= both individual areas (due to overlap and smoothing)
        original_combined = np.sum(sample_mask_1.mask | sample_mask_2.mask)
        # Allow some variation due to smoothing
        assert merged.area >= original_combined * 0.9
    
    def test_merge_creates_smooth_edges(self, sample_mask_1, sample_mask_2):
        """Test that merged mask has smooth edges."""
        import cv2
        
        merged = merge_masks([sample_mask_1, sample_mask_2], smooth_edges=True)
        
        assert merged is not None
        
        # Find contours of the merged mask
        mask_uint8 = merged.mask.astype(np.uint8) * 255
        contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Should have a single contour (merged into one region)
        assert len(contours) == 1
        
        # The contour should be reasonably smooth (not too many points)
        # A very jagged contour would have many more points
        contour = contours[0]
        perimeter = cv2.arcLength(contour, True)
        
        # Smooth contours have fewer points per unit perimeter
        points_per_perimeter = len(contour) / perimeter
        # Typically smooth contours have < 0.1 points per pixel of perimeter
        assert points_per_perimeter < 0.2, f"Contour too jagged: {points_per_perimeter:.3f} points/pixel"
    
    def test_merge_preserves_original_area(self, sample_mask_1, sample_mask_2):
        """Test that merge doesn't lose original pixels."""
        merged = merge_masks([sample_mask_1, sample_mask_2])
        
        assert merged is not None
        
        # All original pixels should be covered by the merged mask
        original_combined = sample_mask_1.mask | sample_mask_2.mask
        covered = merged.mask & original_combined
        coverage = np.sum(covered) / np.sum(original_combined)
        
        # Should cover at least 95% of original area
        assert coverage >= 0.95, f"Coverage too low: {100*coverage:.0f}%"
    
    def test_merge_single_mask(self, sample_mask_1):
        """Test that merging a single mask returns it as-is."""
        merged = merge_masks([sample_mask_1])
        
        assert merged is not None
        assert merged.id == sample_mask_1.id
        assert np.array_equal(merged.mask, sample_mask_1.mask)
    
    def test_merge_empty_list(self):
        """Test that merging empty list returns None."""
        merged = merge_masks([])
        assert merged is None
    
    def test_merge_without_smoothing(self, sample_mask_1, sample_mask_2):
        """Test merging without edge smoothing."""
        merged = merge_masks([sample_mask_1, sample_mask_2], smooth_edges=False)
        
        assert merged is not None
        
        # Without smoothing, the area should be exactly the union
        original_combined = sample_mask_1.mask | sample_mask_2.mask
        assert np.sum(merged.mask) == np.sum(original_combined)
    
    def test_merge_with_custom_id(self, sample_mask_1, sample_mask_2):
        """Test merging with a custom ID."""
        custom_id = "my_merged_fairway_1"
        merged = merge_masks([sample_mask_1, sample_mask_2], new_id=custom_id)
        
        assert merged is not None
        assert merged.id == custom_id


class TestGenerateFilledPolygon:
    """Tests for the generate_filled_polygon() method."""
    
    def test_generate_filled_polygon_basic(self, sample_image):
        """Test basic filled polygon generation."""
        generator = MaskGenerator(checkpoint_path=None)
        generator._sam = None  # Don't need SAM for filled polygon
        
        # Draw a square outline
        outline_points = [
            (50, 50), (100, 50), (100, 100), (50, 100), (50, 50)
        ]
        
        mask_data = generator.generate_filled_polygon(sample_image, outline_points)
        
        assert mask_data is not None
        assert mask_data.area > 0
        assert "filled_polygon" in mask_data.id
        assert mask_data.predicted_iou == 1.0
        assert mask_data.stability_score == 1.0
    
    def test_generate_filled_polygon_smooth_edges(self, sample_image):
        """Test that filled polygon has smooth edges."""
        import cv2
        
        generator = MaskGenerator(checkpoint_path=None)
        generator._sam = None
        
        # Draw a polygon with many points (like a hand-drawn circle)
        import math
        center_x, center_y = 100, 100
        radius = 40
        outline_points = []
        for i in range(50):  # Many points = potentially jagged
            angle = 2 * math.pi * i / 50
            px = center_x + int(radius * math.cos(angle))
            py = center_y + int(radius * math.sin(angle))
            outline_points.append((px, py))
        
        mask_data = generator.generate_filled_polygon(sample_image, outline_points, smooth_edges=True)
        
        assert mask_data is not None
        
        # Check that edges are smooth using polygon approximation
        # A smooth boundary can be well-approximated with fewer points
        mask_uint8 = mask_data.mask.astype(np.uint8) * 255
        contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        assert len(contours) == 1
        contour = contours[0]
        
        # Check smoothness by comparing the contour to its polygon approximation
        # A smooth contour will have a high approximation ratio (few points needed)
        perimeter = cv2.arcLength(contour, True)
        
        # Approximate with small epsilon - should capture the shape well
        epsilon = perimeter * 0.02  # 2% of perimeter
        approx = cv2.approxPolyDP(contour, epsilon, True)
        
        # For a smooth circular shape, approximation should use relatively few points
        # (vs a jagged shape that would need many more points to approximate)
        # A smooth circle can be approximated with ~12-20 points at 2% epsilon
        assert len(approx) < 50, f"Edge not smooth enough: needs {len(approx)} points to approximate"
        
        # Also verify the approximation covers most of the area (no jagged in/out)
        approx_mask = np.zeros_like(mask_uint8)
        cv2.fillPoly(approx_mask, [approx], 255)
        
        # Calculate how well the approximation matches the original
        intersection = np.sum((mask_uint8 > 0) & (approx_mask > 0))
        union = np.sum((mask_uint8 > 0) | (approx_mask > 0))
        iou = intersection / union if union > 0 else 0
        
        # High IoU (>0.9) means the shape is smooth and regular
        assert iou > 0.85, f"Edge smoothness IoU too low: {iou:.2f}"
    
    def test_generate_filled_polygon_too_few_points(self, sample_image):
        """Test that polygon with too few points returns None."""
        generator = MaskGenerator(checkpoint_path=None)
        generator._sam = None
        
        # Only 2 points - can't form a polygon
        outline_points = [(50, 50), (100, 100)]
        
        mask_data = generator.generate_filled_polygon(sample_image, outline_points)
        
        assert mask_data is None


class TestPointBasedSelectorFillAndMerge:
    """Tests for fill and merge functionality in PointBasedSelector."""
    
    def test_fill_polygon_to_mask(self, sample_image, mock_mask_generator):
        """Test creating a filled polygon mask."""
        selector = PointBasedSelector(sample_image, mock_mask_generator)
        
        outline_points = [(60, 60), (100, 60), (100, 100), (60, 100)]
        
        mask_data = selector.fill_polygon_to_mask(
            outline_points,
            hole=1,
            feature_type=FeatureType.FAIRWAY
        )
        
        assert mask_data is not None
        assert "fairway" in mask_data.id
        assert "fill" in mask_data.id
        
        # Verify it was added to selections
        selection = selector.get_selection_for_hole(1)
        assert selection is not None
        assert len(selection.fairways) == 1
    
    def test_merge_selected_masks(self, sample_image, mock_mask_generator):
        """Test merging multiple selected masks."""
        selector = PointBasedSelector(sample_image, mock_mask_generator)
        
        # Create two masks
        outline1 = [(50, 50), (80, 50), (80, 80), (50, 80)]
        mask1 = selector.draw_to_mask(outline1, hole=1, feature_type=FeatureType.FAIRWAY)
        
        outline2 = [(70, 70), (110, 70), (110, 100), (70, 100)]
        mask2 = selector.fill_polygon_to_mask(outline2, hole=1, feature_type=FeatureType.FAIRWAY)
        
        assert mask1 is not None
        assert mask2 is not None
        
        # Merge them
        merged = selector.merge_selected_masks(
            [mask1.id, mask2.id],
            hole=1,
            feature_type=FeatureType.FAIRWAY
        )
        
        assert merged is not None
        assert "merged" in merged.id
        
        # Old masks should be removed from fairways list, merged mask added
        selection = selector.get_selection_for_hole(1)
        assert merged.id in selection.fairways
        assert mask1.id not in selection.fairways
        assert mask2.id not in selection.fairways
    
    def test_merge_requires_two_masks(self, sample_image, mock_mask_generator):
        """Test that merging requires at least 2 masks."""
        selector = PointBasedSelector(sample_image, mock_mask_generator)
        
        # Create only one mask
        outline1 = [(50, 50), (80, 50), (80, 80), (50, 80)]
        mask1 = selector.draw_to_mask(outline1, hole=1, feature_type=FeatureType.FAIRWAY)
        
        # Try to merge single mask
        merged = selector.merge_selected_masks(
            [mask1.id],
            hole=1,
            feature_type=FeatureType.FAIRWAY
        )
        
        assert merged is None


class TestSAMMaskCompletionWorkflow:
    """Integration tests for the complete SAM mask completion workflow."""
    
    def test_complete_workflow_sam_then_fill_then_merge(self, sample_image, mock_mask_generator):
        """Test the complete workflow: SAM mask -> Fill polygon -> Merge."""
        selector = PointBasedSelector(sample_image, mock_mask_generator)
        
        # Step 1: Generate SAM mask (simulated - doesn't fill whole area)
        sam_outline = [(50, 50), (80, 50), (80, 80), (50, 80)]
        sam_mask = selector.draw_to_mask(sam_outline, hole=1, feature_type=FeatureType.GREEN)
        assert sam_mask is not None
        
        # Step 2: User sees gap, draws filled polygon to cover it
        fill_outline = [(75, 75), (120, 75), (120, 110), (75, 110)]
        fill_mask = selector.fill_polygon_to_mask(fill_outline, hole=1, feature_type=FeatureType.GREEN)
        assert fill_mask is not None
        
        # Step 3: Merge both masks
        merged = selector.merge_selected_masks(
            [sam_mask.id, fill_mask.id],
            hole=1,
            feature_type=FeatureType.GREEN
        )
        
        assert merged is not None
        assert "merged" in merged.id
        
        # Final selection should have only the merged mask
        selection = selector.get_selection_for_hole(1)
        assert len(selection.greens) == 1
        assert merged.id in selection.greens
        
        # Merged mask should cover area of both original masks
        assert merged.area >= sam_mask.area
        assert merged.area >= fill_mask.area
    
    def test_workflow_multiple_fill_then_merge(self, sample_image, mock_mask_generator):
        """Test workflow with multiple fill polygons merged together."""
        selector = PointBasedSelector(sample_image, mock_mask_generator)
        
        # Create several filled polygons for a large fairway
        fill1 = selector.fill_polygon_to_mask(
            [(30, 50), (60, 50), (60, 80), (30, 80)],
            hole=1, feature_type=FeatureType.FAIRWAY
        )
        fill2 = selector.fill_polygon_to_mask(
            [(55, 50), (90, 50), (90, 80), (55, 80)],
            hole=1, feature_type=FeatureType.FAIRWAY
        )
        fill3 = selector.fill_polygon_to_mask(
            [(85, 50), (120, 50), (120, 80), (85, 80)],
            hole=1, feature_type=FeatureType.FAIRWAY
        )
        
        # Merge all three
        # Note: current implementation merges 2 at a time
        # First merge fill1 and fill2
        partial_merged = selector.merge_selected_masks(
            [fill1.id, fill2.id],
            hole=1, feature_type=FeatureType.FAIRWAY
        )
        
        # Then merge the result with fill3
        final_merged = selector.merge_selected_masks(
            [partial_merged.id, fill3.id],
            hole=1, feature_type=FeatureType.FAIRWAY
        )
        
        assert final_merged is not None
        
        # Should have one final fairway mask
        selection = selector.get_selection_for_hole(1)
        assert len(selection.fairways) == 1
        assert final_merged.id in selection.fairways
