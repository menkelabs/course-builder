"""
Feature Extraction Module

Extracts color, texture, shape, and context features from masks
for classification.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Any
import logging

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class MaskFeatures:
    """Container for extracted mask features."""
    mask_id: str
    
    # Color features (HSV)
    hsv_mean: tuple = (0.0, 0.0, 0.0)
    hsv_std: tuple = (0.0, 0.0, 0.0)
    
    # Color features (Lab)
    lab_mean: tuple = (0.0, 0.0, 0.0)
    lab_std: tuple = (0.0, 0.0, 0.0)
    
    # Texture features
    grayscale_variance: float = 0.0
    
    # Shape features
    area: int = 0
    perimeter: float = 0.0
    compactness: float = 0.0
    elongation: float = 0.0
    
    # Context features
    neighbor_distances: List[float] = field(default_factory=list)
    water_overlap_ratio: float = 0.0
    green_center_distance: Optional[float] = None
    nearest_hole: Optional[int] = None
    
    def to_dict(self) -> dict:
        """Export features to dictionary."""
        return {
            "mask_id": self.mask_id,
            "color": {
                "hsv_mean": list(self.hsv_mean),
                "hsv_std": list(self.hsv_std),
                "lab_mean": list(self.lab_mean),
                "lab_std": list(self.lab_std),
            },
            "texture": {
                "grayscale_variance": self.grayscale_variance,
            },
            "shape": {
                "area": self.area,
                "perimeter": self.perimeter,
                "compactness": self.compactness,
                "elongation": self.elongation,
            },
            "context": {
                "neighbor_distances": self.neighbor_distances[:5],  # Top 5
                "water_overlap_ratio": self.water_overlap_ratio,
                "green_center_distance": self.green_center_distance,
                "nearest_hole": self.nearest_hole,
            },
        }


class FeatureExtractor:
    """
    Extract features from masks for classification.
    
    Features are computed in several categories:
    - Color: HSV and Lab color space statistics
    - Texture: Grayscale variance
    - Shape: Area, perimeter, compactness, elongation
    - Context: Proximity to other masks, overlap with water, distance to greens
    """
    
    def __init__(
        self,
        green_centers: Optional[List[Dict]] = None,
        water_candidates: Optional[List[np.ndarray]] = None,
    ):
        """
        Initialize the feature extractor.
        
        Args:
            green_centers: List of green center coordinates [{hole, x, y}, ...]
            water_candidates: Pre-identified water mask candidates
        """
        self.green_centers = green_centers or []
        self.water_candidates = water_candidates or []
    
    def extract(
        self,
        mask: np.ndarray,
        mask_id: str,
        image: np.ndarray,
        all_masks: Optional[List[np.ndarray]] = None,
    ) -> MaskFeatures:
        """
        Extract features from a single mask.
        
        Args:
            mask: Binary mask array (H, W)
            mask_id: Identifier for this mask
            image: Source image (H, W, 3) in RGB
            all_masks: List of all masks for context features
            
        Returns:
            MaskFeatures object
        """
        features = MaskFeatures(mask_id=mask_id)
        
        # Extract color features
        self._extract_color_features(mask, image, features)
        
        # Extract texture features
        self._extract_texture_features(mask, image, features)
        
        # Extract shape features
        self._extract_shape_features(mask, features)
        
        # Extract context features
        if all_masks is not None:
            self._extract_context_features(mask, all_masks, features)
        
        return features
    
    def _extract_color_features(
        self,
        mask: np.ndarray,
        image: np.ndarray,
        features: MaskFeatures,
    ) -> None:
        """Extract color statistics in HSV and Lab color spaces."""
        try:
            import cv2
        except ImportError:
            logger.warning("OpenCV not available, skipping color features")
            return
        
        # Get masked pixels
        masked_pixels = image[mask]
        if len(masked_pixels) == 0:
            return
        
        # Convert to HSV
        hsv_image = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        hsv_pixels = hsv_image[mask]
        features.hsv_mean = tuple(np.mean(hsv_pixels, axis=0).tolist())
        features.hsv_std = tuple(np.std(hsv_pixels, axis=0).tolist())
        
        # Convert to Lab
        lab_image = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
        lab_pixels = lab_image[mask]
        features.lab_mean = tuple(np.mean(lab_pixels, axis=0).tolist())
        features.lab_std = tuple(np.std(lab_pixels, axis=0).tolist())
    
    def _extract_texture_features(
        self,
        mask: np.ndarray,
        image: np.ndarray,
        features: MaskFeatures,
    ) -> None:
        """Extract texture features using grayscale variance."""
        try:
            import cv2
        except ImportError:
            logger.warning("OpenCV not available, skipping texture features")
            return
        
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        masked_pixels = gray[mask]
        
        if len(masked_pixels) > 0:
            features.grayscale_variance = float(np.var(masked_pixels))
    
    def _extract_shape_features(
        self,
        mask: np.ndarray,
        features: MaskFeatures,
    ) -> None:
        """Extract shape features: area, perimeter, compactness, elongation."""
        try:
            import cv2
        except ImportError:
            logger.warning("OpenCV not available, skipping shape features")
            return
        
        # Area
        features.area = int(np.sum(mask))
        
        # Find contours
        mask_uint8 = (mask * 255).astype(np.uint8)
        contours, _ = cv2.findContours(
            mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        
        if not contours:
            return
        
        # Use largest contour
        contour = max(contours, key=cv2.contourArea)
        
        # Perimeter
        features.perimeter = float(cv2.arcLength(contour, True))
        
        # Compactness (4 * pi * area / perimeter^2)
        if features.perimeter > 0:
            features.compactness = (4 * np.pi * features.area) / (features.perimeter ** 2)
        
        # Elongation from fitted ellipse
        if len(contour) >= 5:
            ellipse = cv2.fitEllipse(contour)
            (_, axes, _) = ellipse
            if axes[0] > 0:
                features.elongation = axes[1] / axes[0]
    
    def _extract_context_features(
        self,
        mask: np.ndarray,
        all_masks: List[np.ndarray],
        features: MaskFeatures,
    ) -> None:
        """Extract context features based on relationships with other masks."""
        # Compute centroid of this mask
        y_coords, x_coords = np.where(mask)
        if len(y_coords) == 0:
            return
        
        centroid = (np.mean(x_coords), np.mean(y_coords))
        
        # Distance to other mask centroids
        distances = []
        for other_mask in all_masks:
            if np.array_equal(mask, other_mask):
                continue
            other_y, other_x = np.where(other_mask)
            if len(other_y) == 0:
                continue
            other_centroid = (np.mean(other_x), np.mean(other_y))
            dist = np.sqrt(
                (centroid[0] - other_centroid[0]) ** 2 +
                (centroid[1] - other_centroid[1]) ** 2
            )
            distances.append(dist)
        
        features.neighbor_distances = sorted(distances)[:10]
        
        # Distance to nearest green center
        if self.green_centers:
            min_dist = float("inf")
            nearest_hole = None
            for gc in self.green_centers:
                dist = np.sqrt(
                    (centroid[0] - gc["x"]) ** 2 +
                    (centroid[1] - gc["y"]) ** 2
                )
                if dist < min_dist:
                    min_dist = dist
                    nearest_hole = gc.get("hole")
            
            features.green_center_distance = min_dist
            features.nearest_hole = nearest_hole
        
        # Overlap with water candidates
        if self.water_candidates:
            max_overlap = 0.0
            for water_mask in self.water_candidates:
                overlap = np.sum(mask & water_mask)
                overlap_ratio = overlap / max(np.sum(mask), 1)
                max_overlap = max(max_overlap, overlap_ratio)
            features.water_overlap_ratio = max_overlap
    
    def extract_all(
        self,
        masks: List[Any],  # List of MaskData
        image: np.ndarray,
    ) -> List[MaskFeatures]:
        """
        Extract features from all masks.
        
        Args:
            masks: List of MaskData objects
            image: Source image
            
        Returns:
            List of MaskFeatures objects
        """
        all_mask_arrays = [m.mask for m in masks]
        
        features_list = []
        for mask_data in masks:
            features = self.extract(
                mask=mask_data.mask,
                mask_id=mask_data.id,
                image=image,
                all_masks=all_mask_arrays,
            )
            features_list.append(features)
        
        logger.info(f"Extracted features for {len(features_list)} masks")
        return features_list
    
    def save_features(
        self,
        features_list: List[MaskFeatures],
        output_path: Path,
    ) -> None:
        """Save features to JSON file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = [f.to_dict() for f in features_list]
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved features to {output_path}")
    
    @staticmethod
    def load_features(features_path: Path) -> List[MaskFeatures]:
        """Load features from JSON file."""
        with open(features_path) as f:
            data = json.load(f)
        
        features_list = []
        for item in data:
            features = MaskFeatures(
                mask_id=item["mask_id"],
                hsv_mean=tuple(item["color"]["hsv_mean"]),
                hsv_std=tuple(item["color"]["hsv_std"]),
                lab_mean=tuple(item["color"]["lab_mean"]),
                lab_std=tuple(item["color"]["lab_std"]),
                grayscale_variance=item["texture"]["grayscale_variance"],
                area=item["shape"]["area"],
                perimeter=item["shape"]["perimeter"],
                compactness=item["shape"]["compactness"],
                elongation=item["shape"]["elongation"],
                neighbor_distances=item["context"]["neighbor_distances"],
                water_overlap_ratio=item["context"]["water_overlap_ratio"],
                green_center_distance=item["context"]["green_center_distance"],
                nearest_hole=item["context"]["nearest_hole"],
            )
            features_list.append(features)
        
        return features_list
