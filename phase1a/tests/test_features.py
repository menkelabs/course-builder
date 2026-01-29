"""
Tests for feature extraction module.
"""

import json
from pathlib import Path

import numpy as np
import pytest

from phase1a.pipeline.features import FeatureExtractor, MaskFeatures


class TestMaskFeatures:
    """Tests for MaskFeatures dataclass."""
    
    def test_default_values(self):
        features = MaskFeatures(mask_id="test")
        assert features.mask_id == "test"
        assert features.hsv_mean == (0.0, 0.0, 0.0)
        assert features.area == 0
        assert features.compactness == 0.0
    
    def test_to_dict(self):
        features = MaskFeatures(
            mask_id="mask_001",
            hsv_mean=(60.0, 100.0, 150.0),
            area=1000,
            compactness=0.75,
        )
        data = features.to_dict()
        
        assert data["mask_id"] == "mask_001"
        assert data["color"]["hsv_mean"] == [60.0, 100.0, 150.0]
        assert data["shape"]["area"] == 1000
        assert data["shape"]["compactness"] == 0.75


class TestFeatureExtractor:
    """Tests for FeatureExtractor class."""
    
    def test_init_default(self):
        extractor = FeatureExtractor()
        assert extractor.green_centers == []
        assert extractor.water_candidates == []
    
    def test_init_with_green_centers(self, sample_green_centers):
        extractor = FeatureExtractor(green_centers=sample_green_centers)
        assert len(extractor.green_centers) == 3
    
    def test_extract_single_mask(self, sample_mask, sample_image):
        extractor = FeatureExtractor()
        features = extractor.extract(
            mask=sample_mask,
            mask_id="test_mask",
            image=sample_image,
        )
        
        assert features.mask_id == "test_mask"
        assert features.area > 0
        assert features.perimeter > 0
    
    def test_extract_color_features(self, sample_mask, sample_image):
        extractor = FeatureExtractor()
        features = extractor.extract(
            mask=sample_mask,
            mask_id="test",
            image=sample_image,
        )
        
        # HSV should have 3 components
        assert len(features.hsv_mean) == 3
        assert len(features.hsv_std) == 3
        
        # Lab should have 3 components
        assert len(features.lab_mean) == 3
        assert len(features.lab_std) == 3
    
    def test_extract_shape_features(self, sample_mask, sample_image):
        extractor = FeatureExtractor()
        features = extractor.extract(
            mask=sample_mask,
            mask_id="test",
            image=sample_image,
        )
        
        # Area should match mask sum
        assert features.area == np.sum(sample_mask)
        
        # Perimeter should be positive
        assert features.perimeter > 0
        
        # Compactness should be between 0 and 1 for a circle
        assert 0 < features.compactness <= 1.0
    
    def test_extract_context_with_green_centers(
        self, sample_mask, sample_image, sample_green_centers
    ):
        extractor = FeatureExtractor(green_centers=sample_green_centers)
        
        # Need to provide all_masks for context features
        features = extractor.extract(
            mask=sample_mask,
            mask_id="test",
            image=sample_image,
            all_masks=[sample_mask],  # Provide masks for context extraction
        )
        
        # Should have distance to green center
        assert features.green_center_distance is not None
        assert features.green_center_distance >= 0
        
        # Should have nearest hole
        assert features.nearest_hole is not None
    
    def test_extract_all(self, mock_mask_data, sample_image):
        extractor = FeatureExtractor()
        features_list = extractor.extract_all(mock_mask_data, sample_image)
        
        assert len(features_list) == len(mock_mask_data)
        for features in features_list:
            assert isinstance(features, MaskFeatures)
    
    def test_save_and_load_features(self, mock_features, temp_dir):
        extractor = FeatureExtractor()
        output_path = temp_dir / "features.json"
        
        # Save
        extractor.save_features(mock_features, output_path)
        assert output_path.exists()
        
        # Load
        loaded = FeatureExtractor.load_features(output_path)
        assert len(loaded) == len(mock_features)
        
        # Verify content
        for orig, load in zip(mock_features, loaded):
            assert orig.mask_id == load.mask_id
            assert orig.area == load.area


class TestFeatureExtractorEdgeCases:
    """Edge case tests for FeatureExtractor."""
    
    def test_empty_mask(self, sample_image):
        """Test with an empty (all False) mask."""
        extractor = FeatureExtractor()
        empty_mask = np.zeros((256, 256), dtype=bool)
        
        features = extractor.extract(
            mask=empty_mask,
            mask_id="empty",
            image=sample_image,
        )
        
        assert features.area == 0
    
    def test_full_mask(self, sample_image):
        """Test with a full (all True) mask."""
        extractor = FeatureExtractor()
        full_mask = np.ones((256, 256), dtype=bool)
        
        features = extractor.extract(
            mask=full_mask,
            mask_id="full",
            image=sample_image,
        )
        
        assert features.area == 256 * 256
    
    def test_single_pixel_mask(self, sample_image):
        """Test with a single pixel mask."""
        extractor = FeatureExtractor()
        single_mask = np.zeros((256, 256), dtype=bool)
        single_mask[128, 128] = True
        
        features = extractor.extract(
            mask=single_mask,
            mask_id="single",
            image=sample_image,
        )
        
        assert features.area == 1
