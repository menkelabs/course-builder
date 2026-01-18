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
        
        self._sam = None
        self._mask_generator = None
    
    def _load_model(self) -> None:
        """Lazy-load SAM model."""
        if self._sam is not None:
            return
        
        try:
            import torch
            from segment_anything import sam_model_registry, SamAutomaticMaskGenerator
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
        
        logger.info("SAM model loaded successfully")
    
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
