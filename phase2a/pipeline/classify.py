"""
Mask Classification Module

Classifies masks into feature types based on extracted features.
"""

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging

import numpy as np

from .features import MaskFeatures

logger = logging.getLogger(__name__)


class FeatureClass(str, Enum):
    """Golf course feature classifications."""
    WATER = "water"
    BUNKER = "bunker"
    GREEN = "green"
    FAIRWAY = "fairway"
    ROUGH = "rough"
    IGNORE = "ignore"


@dataclass
class Classification:
    """Classification result for a single mask."""
    mask_id: str
    feature_class: FeatureClass
    confidence: float
    scores: Dict[str, float]  # Scores for all classes
    
    def to_dict(self) -> dict:
        """Export to dictionary."""
        return {
            "mask_id": self.mask_id,
            "class": self.feature_class.value,
            "confidence": self.confidence,
            "scores": self.scores,
        }


class MaskClassifier:
    """
    Classify masks into golf course feature types.
    
    Uses heuristic rules based on color, shape, and context features.
    This can be replaced with a trained classifier in future iterations.
    """
    
    # Color thresholds for different features (in HSV)
    # H: 0-180, S: 0-255, V: 0-255
    COLOR_PROFILES = {
        FeatureClass.WATER: {
            "h_range": (90, 130),  # Blue hues
            "s_min": 50,
            "v_range": (50, 200),
        },
        FeatureClass.BUNKER: {
            "h_range": (15, 35),  # Yellow/tan hues
            "s_range": (30, 150),
            "v_min": 150,
        },
        FeatureClass.GREEN: {
            "h_range": (35, 85),  # Green hues
            "s_min": 80,
            "compactness_min": 0.5,  # Greens are typically round
        },
        FeatureClass.FAIRWAY: {
            "h_range": (35, 85),  # Green hues
            "s_range": (40, 150),
            "elongation_min": 1.5,  # Fairways are elongated
        },
        FeatureClass.ROUGH: {
            "h_range": (30, 90),  # Green/brown hues
            "s_range": (20, 100),
            "v_range": (50, 180),
        },
    }
    
    def __init__(
        self,
        min_area: int = 100,
        max_area: Optional[int] = None,
    ):
        """
        Initialize the classifier.
        
        Args:
            min_area: Minimum mask area to consider
            max_area: Maximum mask area to consider (None = no limit)
        """
        self.min_area = min_area
        self.max_area = max_area
    
    def classify(self, features: MaskFeatures) -> Classification:
        """
        Classify a single mask based on its features.
        
        Args:
            features: Extracted mask features
            
        Returns:
            Classification result
        """
        # Calculate scores for each class
        scores = {}
        
        # Check area constraints
        if features.area < self.min_area:
            return Classification(
                mask_id=features.mask_id,
                feature_class=FeatureClass.IGNORE,
                confidence=1.0,
                scores={c.value: 0.0 for c in FeatureClass},
            )
        
        if self.max_area and features.area > self.max_area:
            return Classification(
                mask_id=features.mask_id,
                feature_class=FeatureClass.IGNORE,
                confidence=1.0,
                scores={c.value: 0.0 for c in FeatureClass},
            )
        
        # Score each feature class
        scores[FeatureClass.WATER.value] = self._score_water(features)
        scores[FeatureClass.BUNKER.value] = self._score_bunker(features)
        scores[FeatureClass.GREEN.value] = self._score_green(features)
        scores[FeatureClass.FAIRWAY.value] = self._score_fairway(features)
        scores[FeatureClass.ROUGH.value] = self._score_rough(features)
        scores[FeatureClass.IGNORE.value] = 0.1  # Base ignore score
        
        # Find best class
        best_class = max(scores, key=scores.get)
        best_score = scores[best_class]
        
        # Normalize confidence
        total_score = sum(scores.values())
        confidence = best_score / total_score if total_score > 0 else 0.0
        
        return Classification(
            mask_id=features.mask_id,
            feature_class=FeatureClass(best_class),
            confidence=confidence,
            scores=scores,
        )
    
    def _score_water(self, features: MaskFeatures) -> float:
        """Score likelihood of being water."""
        score = 0.0
        h, s, v = features.hsv_mean
        
        profile = self.COLOR_PROFILES[FeatureClass.WATER]
        
        # Blue hue check
        if profile["h_range"][0] <= h <= profile["h_range"][1]:
            score += 0.4
        
        # Saturation check
        if s >= profile["s_min"]:
            score += 0.2
        
        # Value check
        if profile["v_range"][0] <= v <= profile["v_range"][1]:
            score += 0.2
        
        # Low texture variance (water is smooth)
        if features.grayscale_variance < 500:
            score += 0.2
        
        return score
    
    def _score_bunker(self, features: MaskFeatures) -> float:
        """Score likelihood of being a bunker."""
        score = 0.0
        h, s, v = features.hsv_mean
        
        profile = self.COLOR_PROFILES[FeatureClass.BUNKER]
        
        # Yellow/tan hue check
        if profile["h_range"][0] <= h <= profile["h_range"][1]:
            score += 0.4
        
        # Saturation check
        if profile["s_range"][0] <= s <= profile["s_range"][1]:
            score += 0.2
        
        # High brightness (sand is bright)
        if v >= profile["v_min"]:
            score += 0.2
        
        # Moderate compactness (bunkers are somewhat round)
        if 0.3 <= features.compactness <= 0.8:
            score += 0.2
        
        return score
    
    def _score_green(self, features: MaskFeatures) -> float:
        """Score likelihood of being a green."""
        score = 0.0
        h, s, v = features.hsv_mean
        
        profile = self.COLOR_PROFILES[FeatureClass.GREEN]
        
        # Green hue check
        if profile["h_range"][0] <= h <= profile["h_range"][1]:
            score += 0.3
        
        # High saturation (greens are vivid)
        if s >= profile["s_min"]:
            score += 0.2
        
        # Compactness (greens are round/oval)
        if features.compactness >= profile["compactness_min"]:
            score += 0.3
        
        # Size constraint (greens are medium-sized)
        if 5000 <= features.area <= 50000:
            score += 0.2
        
        return score
    
    def _score_fairway(self, features: MaskFeatures) -> float:
        """Score likelihood of being a fairway."""
        score = 0.0
        h, s, v = features.hsv_mean
        
        profile = self.COLOR_PROFILES[FeatureClass.FAIRWAY]
        
        # Green hue check
        if profile["h_range"][0] <= h <= profile["h_range"][1]:
            score += 0.3
        
        # Moderate saturation
        if profile["s_range"][0] <= s <= profile["s_range"][1]:
            score += 0.2
        
        # Elongation (fairways are long)
        if features.elongation >= profile["elongation_min"]:
            score += 0.3
        
        # Large area
        if features.area > 20000:
            score += 0.2
        
        return score
    
    def _score_rough(self, features: MaskFeatures) -> float:
        """Score likelihood of being rough."""
        score = 0.0
        h, s, v = features.hsv_mean
        
        profile = self.COLOR_PROFILES[FeatureClass.ROUGH]
        
        # Green/brown hue
        if profile["h_range"][0] <= h <= profile["h_range"][1]:
            score += 0.3
        
        # Low saturation (rough is less vivid)
        if profile["s_range"][0] <= s <= profile["s_range"][1]:
            score += 0.2
        
        # Darker value
        if profile["v_range"][0] <= v <= profile["v_range"][1]:
            score += 0.2
        
        # High texture variance
        if features.grayscale_variance > 300:
            score += 0.3
        
        return score
    
    def classify_all(
        self,
        features_list: List[MaskFeatures],
    ) -> List[Classification]:
        """
        Classify all masks.
        
        Args:
            features_list: List of MaskFeatures objects
            
        Returns:
            List of Classification results
        """
        classifications = []
        for features in features_list:
            classification = self.classify(features)
            classifications.append(classification)
        
        # Log summary
        class_counts = {}
        for c in classifications:
            cls = c.feature_class.value
            class_counts[cls] = class_counts.get(cls, 0) + 1
        
        logger.info(f"Classification summary: {class_counts}")
        
        return classifications
    
    def save_classifications(
        self,
        classifications: List[Classification],
        output_path: Path,
    ) -> None:
        """Save classifications to JSON file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = [c.to_dict() for c in classifications]
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved classifications to {output_path}")
    
    @staticmethod
    def load_classifications(path: Path) -> List[Classification]:
        """Load classifications from JSON file."""
        with open(path) as f:
            data = json.load(f)
        
        classifications = []
        for item in data:
            classification = Classification(
                mask_id=item["mask_id"],
                feature_class=FeatureClass(item["class"]),
                confidence=item["confidence"],
                scores=item["scores"],
            )
            classifications.append(classification)
        
        return classifications
