# Grounding DINO Integration Specification

## Overview

Grounding DINO is an open-source, zero-shot object detection model that finds objects in images based on text prompts. It outputs bounding boxes for objects matching the text description.

**Key Properties:**
- Runs 100% locally (no API costs)
- Deterministic outputs (same input = same output)
- Text-to-bounding-box detection
- Integrates natively with SAM for precise segmentation

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ Satellite Image │ ──► │ Grounding DINO   │ ──► │ Bounding Boxes  │
└─────────────────┘     │ + Text Prompts   │     │ per feature     │
                        └──────────────────┘     └────────┬────────┘
                                                          │
                                                          ▼
                        ┌──────────────────┐     ┌─────────────────┐
                        │ Classified Masks │ ◄── │ SAM Segmentation│
                        └──────────────────┘     └─────────────────┘
```

## Installation

```bash
# Option 1: pip install
pip install groundingdino-py

# Option 2: From source
pip install git+https://github.com/IDEA-Research/GroundingDINO.git

# Download model weights (~1.5GB, one-time)
wget https://github.com/IDEA-Research/GroundingDINO/releases/download/v0.1.0-alpha/groundingdino_swint_ogc.pth
```

## Text Prompts for Golf Course Features

| Feature | Recommended Prompts |
|---------|---------------------|
| Green | `"golf green"`, `"putting green"` |
| Fairway | `"fairway"`, `"golf fairway"`, `"mowed grass path"` |
| Bunker | `"sand bunker"`, `"sand trap"`, `"bunker"` |
| Tee | `"tee box"`, `"teeing ground"` |
| Water | `"water hazard"`, `"pond"`, `"lake"` |
| Rough | `"rough grass"`, `"tall grass"` |

## API Specification

### Input

```python
@dataclass
class GroundingDinoInput:
    image: np.ndarray          # RGB image (H, W, 3)
    prompts: List[str]         # Text prompts to detect
    box_threshold: float       # Confidence threshold (default: 0.35)
    text_threshold: float      # Text matching threshold (default: 0.25)
```

### Output

```python
@dataclass
class DetectedBox:
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2) in pixels
    label: str                        # Matched text prompt
    confidence: float                 # Detection confidence (0-1)

@dataclass
class GroundingDinoOutput:
    boxes: List[DetectedBox]
    image_size: Tuple[int, int]       # (width, height)
```

## Implementation

### File: `phase2a/pipeline/grounding_dino.py`

```python
"""
Grounding DINO integration for automated golf course feature detection.
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional
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
    ) -> dict[str, List[DetectedBox]]:
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
```

## Integration with SAM

### File: `phase2a/pipeline/grounded_sam.py`

```python
"""
Grounded SAM: Grounding DINO + SAM for automated segmentation.
"""

from typing import List, Dict, Optional
import numpy as np

from .grounding_dino import GroundingDinoDetector, DetectedBox
from .masks import MaskGenerator, MaskData


class GroundedSAM:
    """
    Combine Grounding DINO detection with SAM segmentation.
    
    Usage:
        gsam = GroundedSAM(
            dino_checkpoint="groundingdino_swint_ogc.pth",
            sam_checkpoint="sam_vit_h_4b8939.pth",
        )
        masks = gsam.detect_and_segment(image, features=["green", "bunker"])
    """
    
    def __init__(
        self,
        dino_checkpoint: str,
        sam_checkpoint: str,
        device: str = "cuda",
    ):
        self.detector = GroundingDinoDetector(
            checkpoint_path=dino_checkpoint,
            device=device,
        )
        self.sam = MaskGenerator(
            checkpoint_path=sam_checkpoint,
            device=device,
        )
    
    def detect_and_segment(
        self,
        image: np.ndarray,
        features: Optional[List[str]] = None,
    ) -> Dict[str, List[MaskData]]:
        """
        Detect golf features and create precise masks.
        
        Args:
            image: RGB image
            features: Feature types to detect (default: all golf features)
            
        Returns:
            Dict mapping feature type to list of MaskData
        """
        # Step 1: Detect with Grounding DINO
        detections = self.detector.detect_golf_features(image, features)
        
        # Step 2: Segment each detection with SAM
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
        
        return results
```

## CLI Integration

Add to `phase2a/cli.py`:

```python
@cli.command()
@click.argument("image", type=click.Path(exists=True, path_type=Path))
@click.option("--dino-checkpoint", required=True, help="Grounding DINO checkpoint")
@click.option("--sam-checkpoint", required=True, help="SAM checkpoint")
@click.option("-o", "--output", type=click.Path(path_type=Path), default=Path("phase2a_output"))
@click.option("--features", multiple=True, default=["green", "fairway", "bunker", "tee"])
@click.option("--device", default="cuda")
def auto_detect(image, dino_checkpoint, sam_checkpoint, output, features, device):
    """
    Automatically detect and segment golf course features.
    
    Uses Grounding DINO for detection + SAM for segmentation.
    No API costs - runs 100% locally.
    """
    from .pipeline.grounded_sam import GroundedSAM
    
    gsam = GroundedSAM(
        dino_checkpoint=dino_checkpoint,
        sam_checkpoint=sam_checkpoint,
        device=device,
    )
    
    # Load image
    from PIL import Image
    img = np.array(Image.open(image).convert("RGB"))
    
    # Detect and segment
    results = gsam.detect_and_segment(img, features=list(features))
    
    # Output results
    for feature, masks in results.items():
        console.print(f"[green]{feature}:[/green] {len(masks)} detected")
```

## Contextual Validation

After detection, validate using golf course spatial rules:

```python
def validate_golf_context(
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
```

## Hardware Requirements

| GPU VRAM | Grounding DINO | SAM | Both Together |
|----------|----------------|-----|---------------|
| 8GB | Yes | Yes (vit_b) | Possible with vit_b |
| 12GB | Yes | Yes (vit_l) | Yes |
| 16GB+ | Yes | Yes (vit_h) | Yes, comfortable |

## Model Files

| Model | Size | Download |
|-------|------|----------|
| Grounding DINO (Swin-T) | 1.5GB | [GitHub Releases](https://github.com/IDEA-Research/GroundingDINO/releases) |
| SAM vit_h | 2.4GB | Already have |

## References

- [Grounding DINO Paper](https://arxiv.org/abs/2303.05499)
- [Grounding DINO GitHub](https://github.com/IDEA-Research/GroundingDINO)
- [Grounded SAM](https://github.com/IDEA-Research/Grounded-Segment-Anything)
