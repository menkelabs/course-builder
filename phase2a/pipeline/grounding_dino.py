"""
Grounding DINO integration for automated golf course feature detection.
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class DetectedBox:
    """A detected bounding box with label and confidence."""
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    label: str
    confidence: float


class GroundingDinoDetector:
    """
    Detect golf course features using Grounding DINO.
    
    Usage:
        detector = GroundingDinoDetector(checkpoint_path="groundingdino_swint_ogc.pth")
        boxes = detector.detect(image, prompts=["golf green", "sand bunker"])
    """
    
    # Default prompts for golf course features
    GOLF_PROMPTS = {
        "green": ["golf green", "putting green"],
        "fairway": ["fairway", "golf fairway"],
        "bunker": ["sand bunker", "sand trap"],
        "tee": ["tee box", "teeing ground"],
        "water": ["water hazard", "pond", "lake"],
        "rough": ["rough grass"],
    }
    
    def __init__(
        self,
        checkpoint_path: str,
        config_path: Optional[str] = None,
        device: str = "cuda",
        box_threshold: float = 0.35,
        text_threshold: float = 0.25,
    ):
        """
        Initialize Grounding DINO detector.
        
        Args:
            checkpoint_path: Path to groundingdino_swint_ogc.pth
            config_path: Path to config file (optional, uses default)
            device: "cuda" or "cpu"
            box_threshold: Minimum confidence for box detection
            text_threshold: Minimum confidence for text matching
        """
        self.checkpoint_path = checkpoint_path
        self.config_path = config_path
        self.device = device
        self.box_threshold = box_threshold
        self.text_threshold = text_threshold
        self._model = None
    
    def _load_model(self):
        """Lazy-load Grounding DINO model."""
        if self._model is not None:
            return
        
        try:
            from groundingdino.util.inference import load_model
        except ImportError:
            raise ImportError(
                "groundingdino is required. Install with:\n"
                "pip install groundingdino-py"
            )
        
        # Use default config if not specified
        if self.config_path is None:
            import groundingdino
            pkg_path = Path(groundingdino.__file__).parent
            self.config_path = str(pkg_path / "config" / "GroundingDINO_SwinT_OGC.py")
        
        logger.info(f"Loading Grounding DINO from {self.checkpoint_path}")
        self._model = load_model(self.config_path, self.checkpoint_path, device=self.device)
        logger.info("Grounding DINO loaded successfully")
    
    def detect(
        self,
        image: np.ndarray,
        prompts: List[str],
        box_threshold: Optional[float] = None,
        text_threshold: Optional[float] = None,
    ) -> List[DetectedBox]:
        """
        Detect objects matching text prompts in the image.
        
        Args:
            image: RGB image as numpy array (H, W, 3)
            prompts: List of text prompts to detect
            box_threshold: Override default box threshold
            text_threshold: Override default text threshold
            
        Returns:
            List of DetectedBox objects
        """
        self._load_model()
        
        from groundingdino.util.inference import predict
        from PIL import Image
        import torch
        
        box_thresh = box_threshold or self.box_threshold
        text_thresh = text_threshold or self.text_threshold
        
        # Convert to PIL Image
        pil_image = Image.fromarray(image)
        
        # Join prompts with " . " as required by Grounding DINO
        caption = " . ".join(prompts)
        
        # Run detection
        boxes, logits, phrases = predict(
            model=self._model,
            image=pil_image,
            caption=caption,
            box_threshold=box_thresh,
            text_threshold=text_thresh,
            device=self.device,
        )
        
        # Convert normalized boxes to pixel coordinates
        height, width = image.shape[:2]
        detected = []
        
        for box, confidence, label in zip(boxes, logits, phrases):
            # box is in (cx, cy, w, h) normalized format
            cx, cy, w, h = box.tolist()
            x1 = int((cx - w/2) * width)
            y1 = int((cy - h/2) * height)
            x2 = int((cx + w/2) * width)
            y2 = int((cy + h/2) * height)
            
            detected.append(DetectedBox(
                bbox=(x1, y1, x2, y2),
                label=label,
                confidence=float(confidence),
            ))
        
        logger.info(f"Detected {len(detected)} objects for prompts: {prompts}")
        return detected
    
    def detect_golf_features(
        self,
        image: np.ndarray,
        features: Optional[List[str]] = None,
    ) -> Dict[str, List[DetectedBox]]:
        """
        Detect golf course features using predefined prompts.
        
        Args:
            image: RGB image as numpy array
            features: List of feature types to detect (default: all)
                      Options: "green", "fairway", "bunker", "tee", "water", "rough"
        
        Returns:
            Dict mapping feature type to list of detected boxes
        """
        if features is None:
            features = list(self.GOLF_PROMPTS.keys())
        
        results = {}
        
        for feature in features:
            if feature not in self.GOLF_PROMPTS:
                logger.warning(f"Unknown feature type: {feature}")
                continue
            
            prompts = self.GOLF_PROMPTS[feature]
            boxes = self.detect(image, prompts)
            
            # Tag all boxes with the feature type
            for box in boxes:
                box.label = feature  # Normalize to feature type
            
            results[feature] = boxes
        
        return results
