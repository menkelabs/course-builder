"""
Grounded SAM: Grounding DINO + SAM for automated segmentation.
"""

from typing import List, Dict, Optional, Tuple
import numpy as np
import logging

from .grounding_dino import GroundingDinoDetector, DetectedBox
from .masks import MaskGenerator, MaskData

logger = logging.getLogger(__name__)


def masks_overlap_or_adjacent(mask1: MaskData, mask2: MaskData, adjacency_threshold: int = 10) -> bool:
    """
    Check if two masks overlap or are adjacent within a threshold.
    
    Args:
        mask1: First mask
        mask2: Second mask
        adjacency_threshold: Max distance in pixels to consider adjacent
        
    Returns:
        True if overlapping or adjacent
    """
    # Quick bbox check first
    x1_min, y1_min, w1, h1 = mask1.bbox
    x1_max, y1_max = x1_min + w1, y1_min + h1
    
    x2_min, y2_min, w2, h2 = mask2.bbox
    x2_max, y2_max = x2_min + w2, y2_min + h2
    
    # Expand bbox by threshold for check
    if (x1_max + adjacency_threshold < x2_min or 
        x1_min - adjacency_threshold > x2_max or 
        y1_max + adjacency_threshold < y2_min or 
        y1_min - adjacency_threshold > y2_max):
        return False
        
    # Detailed mask check
    # If shapes match (should be same image size usually)
    if mask1.mask.shape != mask2.mask.shape:
        # If different shapes, we can't easily compare masks directly without placement
        # Assume bbox check is sufficient or return False
        return False
        
    # Check overlap
    overlap = np.any(mask1.mask & mask2.mask)
    if overlap:
        return True
        
    if adjacency_threshold > 0:
        import cv2
        # Dilate mask1
        kernel_size = adjacency_threshold * 2 + 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        dilated = cv2.dilate(mask1.mask.astype(np.uint8), kernel)
        return np.any(dilated & mask2.mask)
        
    return False


class GroundedSAM:
    """
    Combine Grounding DINO detection with SAM segmentation.
    
    Usage:
        gsam = GroundedSAM(
            dino_checkpoint="groundingdino_swint_ogc.pth",
            sam_checkpoint="sam_vit_h_4b8939.pth",
        )
        masks = gsam.detect_and_segment(image, features=["green", "bunker"])
    
    Note: For GPUs with 12GB or less VRAM, use model_type="vit_b" to avoid OOM errors.
    """
    
    def __init__(
        self,
        dino_checkpoint: str,
        sam_checkpoint: str,
        device: str = "cuda",
        model_type: str = "vit_b",  # Default to vit_b for memory efficiency with DINO
    ):
        self.dino_checkpoint = dino_checkpoint
        self.sam_checkpoint = sam_checkpoint
        self.device = device
        self.model_type = model_type
        
        # Lazy loading - don't load models until needed
        self._detector = None
        self._sam = None
    
    @property
    def detector(self) -> GroundingDinoDetector:
        if self._detector is None:
            self._detector = GroundingDinoDetector(
                checkpoint_path=self.dino_checkpoint,
                device=self.device,
            )
        return self._detector
    
    @property
    def sam(self) -> MaskGenerator:
        if self._sam is None:
            self._sam = MaskGenerator(
                checkpoint_path=self.sam_checkpoint,
                device=self.device,
                model_type=self.model_type,
            )
        return self._sam
    
    def _clear_dino_memory(self):
        """Clear DINO model from GPU memory to make room for SAM."""
        if self._detector is not None and self._detector._model is not None:
            import torch
            del self._detector._model
            self._detector._model = None
            self._detector = None
            torch.cuda.empty_cache()
            logger.info("Cleared DINO from GPU memory")
    
    def detect_and_segment(
        self,
        image: np.ndarray,
        features: Optional[List[str]] = None,
        clear_between: bool = True,
    ) -> Dict[str, List[MaskData]]:
        """
        Detect golf features and create precise masks.
        
        Args:
            image: RGB image
            features: Feature types to detect (default: all golf features)
            clear_between: Clear DINO from GPU before loading SAM (saves ~4GB VRAM)
            
        Returns:
            Dict mapping feature type to list of MaskData
        """
        # Step 1: Detect with Grounding DINO
        logger.info("Running Grounding DINO detection...")
        detections = self.detector.detect_golf_features(image, features)
        
        total_boxes = sum(len(boxes) for boxes in detections.values())
        logger.info(f"DINO detected {total_boxes} boxes across {len(detections)} feature types")
        
        # Clear DINO from memory before loading SAM
        if clear_between:
            self._clear_dino_memory()
        
        # Step 2: Segment each detection with SAM
        logger.info(f"Running SAM segmentation (model_type={self.model_type})...")
        results = {}
        
        for feature_type, boxes in detections.items():
            masks = []
            
            for i, box in enumerate(boxes):
                # Use box prompt for SAM
                mask_data = self.sam.generate_from_box(
                    image,
                    box=box.bbox,
                )
                
                if mask_data:
                    mask_data.id = f"{feature_type}_{i:04d}"
                    masks.append(mask_data)
            
            results[feature_type] = masks
            logger.info(f"  {feature_type}: {len(masks)} masks from {len(boxes)} detections")
        
        return results

    def validate_golf_context(
        self,
        detections: Dict[str, List[MaskData]],
        image_shape: Tuple[int, int],
    ) -> Dict[str, List[Tuple[MaskData, float]]]:
        """
        Score detections based on golf course spatial rules.
        
        Returns masks with confidence scores (0-1).
        """
        scored = {}
        
        greens = detections.get("green", [])
        fairways = detections.get("fairway", [])
        bunkers = detections.get("bunker", [])
        
        for feature_type, masks in detections.items():
            scored[feature_type] = []
            
            for mask in masks:
                score = 1.0
                
                if feature_type == "green":
                    # Greens should be reasonable size (0.1% - 2% of image)
                    area_ratio = mask.area / (image_shape[0] * image_shape[1])
                    if area_ratio < 0.001 or area_ratio > 0.02:
                        score *= 0.5
                    
                    # Greens should have bunkers nearby
                    has_nearby_bunker = any(
                        masks_overlap_or_adjacent(mask, b) for b in bunkers
                    )
                    if not has_nearby_bunker:
                        score *= 0.8
                
                elif feature_type == "bunker":
                    # Bunkers should be near greens or fairways
                    near_green = any(masks_overlap_or_adjacent(mask, g) for g in greens)
                    near_fairway = any(masks_overlap_or_adjacent(mask, f) for f in fairways)
                    if not (near_green or near_fairway):
                        score *= 0.6
                
                scored[feature_type].append((mask, score))
        
        return scored
