"""Configuration for Phase 1.1 SegFormer pipeline."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


# Class set aligned with Danish Golf Courses + phase1a features
CLASS_IDS = {
    "background": 0,
    "fairway": 1,
    "green": 2,
    "tee": 3,
    "bunker": 4,
    "water": 5,
}
CLASS_NAMES = {v: k for k, v in CLASS_IDS.items()}

# Overlap resolution priority (higher = subtract first when polygonizing)
# water > bunker > green > tee > fairway > background
PRIORITY_ORDER: List[str] = ["water", "bunker", "green", "tee", "fairway", "background"]


@dataclass
class SegFormerConfig:
    """SegFormer model and training config."""

    model_size: str = "b3"  # b0, b2, b3
    input_size: int = 512  # crop/tile size (512, 768, or 1024)
    num_classes: int = len(CLASS_IDS)
    learning_rate: float = 6e-5
    batch_size: int = 8
    epochs: int = 50


@dataclass
class InferenceConfig:
    """Inference config (Roboflow vs self-hosted)."""

    mode: str = "self_hosted"  # "roboflow" | "self_hosted"
    model_path: Optional[Path] = None
    roboflow_api_key: Optional[str] = None
    roboflow_workspace: Optional[str] = None
    roboflow_project: Optional[str] = None
    device: str = "cuda"


@dataclass
class PolygonConfig:
    """Masks → polygons (contours, simplify, overlap resolution)."""

    simplify_tolerance: float = 2.0  # Douglas–Peucker
    min_area: float = 50.0
    smooth_edges: bool = True  # optional smoothing; avoid over-smoothing greens
    priority_order: List[str] = field(default_factory=lambda: list(PRIORITY_ORDER))


@dataclass
class SAM2RefineConfig:
    """Optional SAM 2 edge refinement."""

    enabled: bool = False
    checkpoint_path: Optional[Path] = None
    prompt: str = "box"  # "box" | "points"
    device: str = "cuda"


@dataclass
class Phase11Config:
    """Main config for Phase 1.1."""

    # Paths
    input_image: Optional[Path] = None
    output_dir: Path = field(default_factory=lambda: Path("phase1_1_output"))
    dataset_dir: Optional[Path] = None  # Danish Golf Courses (Kaggle)

    segformer: SegFormerConfig = field(default_factory=SegFormerConfig)
    inference: InferenceConfig = field(default_factory=InferenceConfig)
    polygon: PolygonConfig = field(default_factory=PolygonConfig)
    sam2_refine: SAM2RefineConfig = field(default_factory=SAM2RefineConfig)

    verbose: bool = False
