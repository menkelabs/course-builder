"""
Tests for mask classification module.
"""

import json
from pathlib import Path

import pytest

from phase2a.pipeline.classify import (
    MaskClassifier,
    Classification,
    FeatureClass,
)
from phase2a.pipeline.features import MaskFeatures


class TestFeatureClass:
    """Tests for FeatureClass enum."""
    
    def test_all_classes_exist(self):
        assert FeatureClass.WATER == "water"
        assert FeatureClass.BUNKER == "bunker"
        assert FeatureClass.GREEN == "green"
        assert FeatureClass.FAIRWAY == "fairway"
        assert FeatureClass.ROUGH == "rough"
        assert FeatureClass.IGNORE == "ignore"
    
    def test_string_conversion(self):
        assert FeatureClass.WATER.value == "water"
        assert FeatureClass("bunker") == FeatureClass.BUNKER


class TestClassification:
    """Tests for Classification dataclass."""
    
    def test_to_dict(self):
        classification = Classification(
            mask_id="mask_001",
            feature_class=FeatureClass.GREEN,
            confidence=0.85,
            scores={"green": 0.85, "fairway": 0.1, "rough": 0.05},
        )
        data = classification.to_dict()
        
        assert data["mask_id"] == "mask_001"
        assert data["class"] == "green"
        assert data["confidence"] == 0.85
        assert "scores" in data


class TestMaskClassifier:
    """Tests for MaskClassifier class."""
    
    def test_init_default(self):
        classifier = MaskClassifier()
        assert classifier.min_area == 100
        assert classifier.max_area is None
    
    def test_init_custom(self):
        classifier = MaskClassifier(min_area=50, max_area=10000)
        assert classifier.min_area == 50
        assert classifier.max_area == 10000
    
    def test_classify_small_area_ignored(self):
        """Masks below min_area should be classified as IGNORE."""
        classifier = MaskClassifier(min_area=100)
        features = MaskFeatures(mask_id="small", area=50)
        
        result = classifier.classify(features)
        
        assert result.feature_class == FeatureClass.IGNORE
        assert result.confidence == 1.0
    
    def test_classify_large_area_ignored(self):
        """Masks above max_area should be classified as IGNORE."""
        classifier = MaskClassifier(min_area=10, max_area=100)
        features = MaskFeatures(mask_id="large", area=200)
        
        result = classifier.classify(features)
        
        assert result.feature_class == FeatureClass.IGNORE
    
    def test_classify_water_features(self):
        """Test classification of water-like features."""
        classifier = MaskClassifier(min_area=10)
        
        # Water-like: blue hue, moderate saturation, smooth texture
        features = MaskFeatures(
            mask_id="water",
            hsv_mean=(110, 100, 150),  # Blue hue
            grayscale_variance=200,  # Low variance (smooth)
            area=1000,
        )
        
        result = classifier.classify(features)
        
        # Water should score reasonably high
        assert result.scores["water"] > 0.3
    
    def test_classify_bunker_features(self):
        """Test classification of bunker-like features."""
        classifier = MaskClassifier(min_area=10)
        
        # Bunker-like: tan/yellow hue, high brightness
        features = MaskFeatures(
            mask_id="bunker",
            hsv_mean=(25, 80, 200),  # Yellow/tan hue, high value
            compactness=0.5,
            area=500,
        )
        
        result = classifier.classify(features)
        
        # Bunker should score reasonably high
        assert result.scores["bunker"] > 0.3
    
    def test_classify_green_features(self):
        """Test classification of green-like features."""
        classifier = MaskClassifier(min_area=10)
        
        # Green-like: green hue, high saturation, round shape
        features = MaskFeatures(
            mask_id="green",
            hsv_mean=(60, 120, 100),  # Green hue, high saturation
            compactness=0.7,  # Round
            area=15000,  # Medium size
        )
        
        result = classifier.classify(features)
        
        # Green should score reasonably high
        assert result.scores["green"] > 0.3
    
    def test_classify_fairway_features(self):
        """Test classification of fairway-like features."""
        classifier = MaskClassifier(min_area=10)
        
        # Fairway-like: green hue, moderate saturation, elongated
        features = MaskFeatures(
            mask_id="fairway",
            hsv_mean=(55, 80, 120),  # Green hue
            elongation=2.5,  # Elongated
            area=50000,  # Large area
        )
        
        result = classifier.classify(features)
        
        # Fairway should score reasonably high
        assert result.scores["fairway"] > 0.3
    
    def test_classify_rough_features(self):
        """Test classification of rough-like features."""
        classifier = MaskClassifier(min_area=10)
        
        # Rough-like: green/brown hue, low saturation, high texture
        features = MaskFeatures(
            mask_id="rough",
            hsv_mean=(45, 50, 100),  # Green/brown, low sat, darker
            grayscale_variance=500,  # High texture
            area=5000,
        )
        
        result = classifier.classify(features)
        
        # Rough should score reasonably high
        assert result.scores["rough"] > 0.2
    
    def test_classify_all(self, mock_features):
        """Test batch classification."""
        classifier = MaskClassifier(min_area=10)
        classifications = classifier.classify_all(mock_features)
        
        assert len(classifications) == len(mock_features)
        for c in classifications:
            assert isinstance(c, Classification)
            assert c.feature_class in FeatureClass
            assert 0 <= c.confidence <= 1
    
    def test_save_and_load_classifications(self, mock_classifications, temp_dir):
        """Test saving and loading classifications."""
        classifier = MaskClassifier()
        output_path = temp_dir / "classifications.json"
        
        # Save
        classifier.save_classifications(mock_classifications, output_path)
        assert output_path.exists()
        
        # Load
        loaded = MaskClassifier.load_classifications(output_path)
        assert len(loaded) == len(mock_classifications)
        
        # Verify
        for orig, load in zip(mock_classifications, loaded):
            assert orig.mask_id == load.mask_id
            assert orig.feature_class == load.feature_class
            assert orig.confidence == load.confidence


class TestClassifierConfidence:
    """Tests for classification confidence calculation."""
    
    def test_confidence_normalized(self):
        """Confidence should be normalized between 0 and 1."""
        classifier = MaskClassifier(min_area=10)
        features = MaskFeatures(
            mask_id="test",
            hsv_mean=(60, 100, 100),
            area=1000,
        )
        
        result = classifier.classify(features)
        
        assert 0 <= result.confidence <= 1
    
    def test_scores_sum_positive(self):
        """All scores should be non-negative."""
        classifier = MaskClassifier(min_area=10)
        features = MaskFeatures(
            mask_id="test",
            hsv_mean=(60, 100, 100),
            area=1000,
        )
        
        result = classifier.classify(features)
        
        for score in result.scores.values():
            assert score >= 0
