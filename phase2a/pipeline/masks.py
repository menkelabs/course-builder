"""
Mask Generation Module

Generates candidate masks using SAM (Segment Anything Model)
automatic mask generation.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Any
import logging

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class MaskData:
    """Container for a single mask and its metadata."""
    id: str
    mask: np.ndarray
    area: int
    bbox: tuple  # (x, y, w, h)
    predicted_iou: float
    stability_score: float
    
    def to_dict(self) -> dict:
        """Export metadata to dictionary (excludes mask array)."""
        return {
            "id": self.id,
            "area": self.area,
            "bbox": list(self.bbox),
            "predicted_iou": self.predicted_iou,
            "stability_score": self.stability_score,
        }


class MaskGenerator:
    """
    Generate candidate masks using SAM automatic mask generation.
    
    This class wraps SAM's automatic mask generator to produce
    candidate masks from satellite imagery.
    """
    
    def __init__(
        self,
        model_type: str = "vit_h",
        checkpoint_path: Optional[str] = None,
        device: str = "cuda",
        points_per_side: int = 32,
        pred_iou_thresh: float = 0.88,
        stability_score_thresh: float = 0.95,
        min_mask_region_area: int = 100,
        point_mask_box_size: Optional[int] = None,  # Box size for point-based masks
    ):
        """
        Initialize the mask generator.
        
        Args:
            model_type: SAM model variant ('vit_h', 'vit_l', 'vit_b')
            checkpoint_path: Path to SAM checkpoint file
            device: Device to run inference on ('cuda' or 'cpu')
            points_per_side: Number of points per side for grid sampling
            pred_iou_thresh: Predicted IoU threshold for filtering
            stability_score_thresh: Stability score threshold
            min_mask_region_area: Minimum mask area in pixels
        """
        self.model_type = model_type
        self.checkpoint_path = checkpoint_path
        self.device = device
        self.points_per_side = points_per_side
        self.pred_iou_thresh = pred_iou_thresh
        self.stability_score_thresh = stability_score_thresh
        self.min_mask_region_area = min_mask_region_area
        self.point_mask_box_size = point_mask_box_size
        
        self._sam = None
        self._mask_generator = None
        self._predictor = None
    
    def _load_model(self) -> None:
        """Lazy-load SAM model."""
        if self._sam is not None:
            return
        
        try:
            import torch
            from segment_anything import sam_model_registry, SamAutomaticMaskGenerator, SamPredictor
        except ImportError:
            raise ImportError(
                "segment-anything is required for mask generation. "
                "Install with: pip install git+https://github.com/facebookresearch/segment-anything.git"
            )
        
        if self.checkpoint_path is None:
            raise ValueError(
                "SAM checkpoint path is required. Download from: "
                "https://github.com/facebookresearch/segment-anything#model-checkpoints"
            )
        
        logger.info(f"Loading SAM model ({self.model_type}) from {self.checkpoint_path}")
        
        self._sam = sam_model_registry[self.model_type](checkpoint=self.checkpoint_path)
        self._sam.to(device=self.device)
        
        self._mask_generator = SamAutomaticMaskGenerator(
            model=self._sam,
            points_per_side=self.points_per_side,
            pred_iou_thresh=self.pred_iou_thresh,
            stability_score_thresh=self.stability_score_thresh,
            min_mask_region_area=self.min_mask_region_area,
        )
        
        # Also create predictor for point-based mask generation
        self._predictor = SamPredictor(self._sam)
        
        logger.info("SAM model loaded successfully")
    
    def generate_from_point(
        self,
        image: np.ndarray,
        point: tuple,  # (x, y) in image coordinates
        label: int = 1,  # 1 = foreground point, 0 = background point
        box_size: Optional[int] = None,  # Optional bounding box size to constrain search
    ) -> Optional[MaskData]:
        """
        Generate a mask from a point prompt, growing outward from the point.
        
        Args:
            image: Input image as numpy array (H, W, 3) in RGB format
            point: Point coordinates (x, y) in image space
            label: Point label (1 = foreground, 0 = background)
            box_size: Optional bounding box size (pixels) to constrain initial search area.
                     If None, uses adaptive size based on image dimensions.
            
        Returns:
            MaskData object or None if generation fails
        """
        self._load_model()
        
        x, y = point
        height, width = image.shape[:2]
        
        # Validate point
        if x < 0 or x >= width or y < 0 or y >= height:
            logger.warning(f"Point ({x}, {y}) is outside image bounds ({width}, {height})")
            return None
        
        # Set image for predictor
        self._predictor.set_image(image)
        
        # Generate mask from point
        input_point = np.array([[x, y]])
        input_label = np.array([label])
        
        # Optionally add a bounding box constraint to focus on local area
        # This helps SAM grow outward from the point rather than finding distant objects
        box = None
        if box_size is None:
            # Adaptive box size: use ~5% of image dimension, but at least 100px
            box_size = max(100, min(width, height) // 20)
        
        # Try multiple approaches to find the best mask that captures texture/color boundaries
        all_masks = []
        all_scores = []
        all_logits = []
        
        # Strategy 1: Try with progressively larger boxes to capture full features
        box_sizes_to_try = []
        if box_size is not None:
            box_sizes_to_try = [box_size]
        elif self.point_mask_box_size is not None:
            box_sizes_to_try = [self.point_mask_box_size]
        else:
            # Try multiple box sizes: small (local), medium (feature), large (context)
            base_size = max(200, min(width, height) // 15)  # Larger base size
            box_sizes_to_try = [
                base_size,           # Local area
                base_size * 2,        # Feature area
                base_size * 4,        # Context area
            ]
        
        # Try with different box sizes
        for box_size_try in box_sizes_to_try:
            box_half = box_size_try // 2
            box_x0 = max(0, x - box_half)
            box_y0 = max(0, y - box_half)
            box_x1 = min(width, x + box_half)
            box_y1 = min(height, y + box_half)
            box = np.array([box_x0, box_y0, box_x1, box_y1])
            
            masks_box, scores_box, logits_box = self._predictor.predict(
                point_coords=input_point,
                point_labels=input_label,
                box=box,
                multimask_output=True,
            )
            
            if len(masks_box) > 0:
                all_masks.extend(masks_box)
                all_scores.extend(scores_box)
                all_logits.extend(logits_box)
        
        # Strategy 2: Also try without box constraint to capture larger features
        masks_no_box, scores_no_box, logits_no_box = self._predictor.predict(
            point_coords=input_point,
            point_labels=input_label,
            multimask_output=True,
        )
        
        if len(masks_no_box) > 0:
            all_masks.extend(masks_no_box)
            all_scores.extend(scores_no_box)
            all_logits.extend(logits_no_box)
        
        # Use all collected masks
        if len(all_masks) == 0:
            return None
        
        masks = all_masks
        scores = np.array(all_scores)
        
        if len(masks) == 0:
            return None
        
        # Select mask that best captures texture/color boundaries
        # Consider: IoU score, proximity to point, and boundary quality
        mask_areas = [np.sum(m) for m in masks]
        point_distances = []
        boundary_scores = []  # Measure of how well mask follows boundaries
        
        for mask in masks:
            # Find centroid of mask
            y_coords, x_coords = np.where(mask)
            if len(y_coords) > 0:
                centroid_x = x_coords.mean()
                centroid_y = y_coords.mean()
                # Distance from click point to mask centroid
                dist = np.sqrt((centroid_x - x)**2 + (centroid_y - y)**2)
                point_distances.append(dist)
                
                # Check if point is inside mask (good sign)
                point_inside = mask[int(y), int(x)] if 0 <= int(y) < height and 0 <= int(x) < width else False
                
                # Estimate boundary quality: masks with good boundaries have
                # reasonable area (not too small, not too large)
                # and the point should be inside or very close
                area = len(y_coords)  # Calculate area from coordinates
                reasonable_size = 1000 <= area <= (width * height * 0.1)  # 0.1% to 10% of image
                boundary_quality = 1.0 if (point_inside or dist < 50) and reasonable_size else 0.5
                boundary_scores.append(boundary_quality)
            else:
                point_distances.append(float('inf'))
                boundary_scores.append(0.0)
        
        # Combined scoring: prioritize masks that capture full features
        # Weight: 50% IoU score, 25% proximity, 25% boundary quality
        combined_scores = []
        for i in range(len(masks)):
            score = float(scores[i])
            area = mask_areas[i]
            dist = point_distances[i]
            boundary = boundary_scores[i]
            
            # Normalize distance (use image diagonal as reference)
            max_dist = np.sqrt(width**2 + height**2)
            normalized_dist = dist / max_dist if max_dist > 0 else 1.0
            
            # Prefer masks that:
            # 1. Have high IoU (good segmentation quality)
            # 2. Are reasonably close to the point (not distant objects)
            # 3. Have good boundary quality (capture full features, point inside)
            # 4. Have reasonable size (not tiny, not huge)
            
            # Size bonus: prefer medium-sized masks that capture full features
            # Ideal size is around 0.5-2% of image area
            ideal_area = (width * height) * 0.01  # 1% of image
            size_ratio = area / ideal_area if ideal_area > 0 else 1.0
            if 0.5 <= size_ratio <= 2.0:
                size_bonus = 1.0
            elif size_ratio < 0.5:
                size_bonus = size_ratio * 2  # Penalize too small
            else:
                size_bonus = max(0.5, 2.0 / size_ratio)  # Penalize too large
            
            combined = (0.5 * score + 
                       0.25 * (1.0 - min(1.0, normalized_dist * 2)) +  # Proximity (less penalty)
                       0.15 * boundary +
                       0.10 * size_bonus)
            combined_scores.append(combined)
        
        best_idx = np.argmax(combined_scores)
        mask = masks[best_idx]
        score = float(scores[best_idx])
        
        logger.debug(f"Selected mask {best_idx}: score={score:.3f}, area={mask_areas[best_idx]}, "
                    f"dist={point_distances[best_idx]:.1f}, combined={combined_scores[best_idx]:.3f}")
        
        # Convert to MaskData
        mask_area = int(np.sum(mask))
        if mask_area < self.min_mask_region_area:
            logger.debug(f"Generated mask too small ({mask_area} < {self.min_mask_region_area})")
            return None
        
        # Calculate bounding box
        y_coords, x_coords = np.where(mask)
        if len(y_coords) == 0:
            return None
        
        bbox = (
            int(x_coords.min()),
            int(y_coords.min()),
            int(x_coords.max() - x_coords.min()),
            int(y_coords.max() - y_coords.min()),
        )
        
        mask_data = MaskData(
            id=f"point_mask_{x}_{y}",
            mask=mask,
            area=mask_area,
            bbox=bbox,
            predicted_iou=score,
            stability_score=score,
        )
        
        logger.debug(f"Generated mask from point ({x}, {y}): area={mask_area}, score={score:.3f}")
        return mask_data
    
    def generate(self, image: np.ndarray) -> List[MaskData]:
        """
        Generate masks from an image.
        
        Args:
            image: Input image as numpy array (H, W, 3) in RGB format
            
        Returns:
            List of MaskData objects containing masks and metadata
        """
        self._load_model()
        
        logger.info(f"Generating masks for image of shape {image.shape}")
        
        # Run SAM automatic mask generation
        sam_masks = self._mask_generator.generate(image)
        
        logger.info(f"Generated {len(sam_masks)} candidate masks")
        
        # Convert to MaskData objects
        masks = []
        for i, sam_mask in enumerate(sam_masks):
            mask_data = MaskData(
                id=f"mask_{i:04d}",
                mask=sam_mask["segmentation"],
                area=sam_mask["area"],
                bbox=tuple(sam_mask["bbox"]),
                predicted_iou=sam_mask["predicted_iou"],
                stability_score=sam_mask["stability_score"],
            )
            masks.append(mask_data)
        
        return masks
    
    def generate_from_file(self, image_path: Path) -> List[MaskData]:
        """
        Generate masks from an image file.
        
        Args:
            image_path: Path to input image
            
        Returns:
            List of MaskData objects
        """
        logger.info(f"Loading image from {image_path}")
        image = np.array(Image.open(image_path).convert("RGB"))
        return self.generate(image)
    
    def save_masks(
        self,
        masks: List[MaskData],
        output_dir: Path,
    ) -> None:
        """
        Save masks to disk.
        
        Args:
            masks: List of MaskData objects
            output_dir: Directory to save masks
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for mask_data in masks:
            # Save mask as PNG
            mask_path = output_dir / f"{mask_data.id}.png"
            mask_img = Image.fromarray((mask_data.mask * 255).astype(np.uint8))
            mask_img.save(mask_path)
            
            # Save metadata as JSON
            meta_path = output_dir / f"{mask_data.id}.json"
            with open(meta_path, "w") as f:
                json.dump(mask_data.to_dict(), f, indent=2)
        
        logger.info(f"Saved {len(masks)} masks to {output_dir}")
    
    @staticmethod
    def load_masks(masks_dir: Path) -> List[MaskData]:
        """
        Load masks from disk.
        
        Args:
            masks_dir: Directory containing saved masks
            
        Returns:
            List of MaskData objects
        """
        masks_dir = Path(masks_dir)
        masks = []
        
        for meta_path in sorted(masks_dir.glob("*.json")):
            with open(meta_path) as f:
                meta = json.load(f)
            
            mask_path = masks_dir / f"{meta['id']}.png"
            mask_img = Image.open(mask_path)
            mask = np.array(mask_img) > 127
            
            mask_data = MaskData(
                id=meta["id"],
                mask=mask,
                area=meta["area"],
                bbox=tuple(meta["bbox"]),
                predicted_iou=meta["predicted_iou"],
                stability_score=meta["stability_score"],
            )
            masks.append(mask_data)
        
        logger.info(f"Loaded {len(masks)} masks from {masks_dir}")
        return masks


# Standalone function for simple usage
def generate_masks(
    image_path: Path,
    output_dir: Path,
    checkpoint_path: str,
    **kwargs: Any,
) -> List[MaskData]:
    """
    Convenience function to generate and save masks.
    
    Args:
        image_path: Path to input image
        output_dir: Directory to save masks
        checkpoint_path: Path to SAM checkpoint
        **kwargs: Additional arguments for MaskGenerator
        
    Returns:
        List of MaskData objects
    """
    generator = MaskGenerator(checkpoint_path=checkpoint_path, **kwargs)
    masks = generator.generate_from_file(image_path)
    generator.save_masks(masks, output_dir)
    return masks
