"""
Configuration for Phase 2A pipeline.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List
import json
import yaml


@dataclass
class ThresholdConfig:
    """Confidence thresholds for mask classification gating."""
    high: float = 0.85
    low: float = 0.5


@dataclass
class SAMConfig:
    """Configuration for SAM mask generation."""
    model_type: str = "vit_h"
    checkpoint_path: Optional[str] = None
    points_per_side: int = 32
    pred_iou_thresh: float = 0.88
    stability_score_thresh: float = 0.95
    min_mask_region_area: int = 100


@dataclass
class PolygonConfig:
    """Configuration for polygon generation."""
    simplify_tolerance: float = 2.0
    min_area: float = 50.0
    buffer_distance: float = 0.0


@dataclass
class SVGConfig:
    """Configuration for SVG generation."""
    width: int = 4096
    height: int = 4096
    stroke_width: float = 1.0
    
    # OPCD color palette
    colors: dict = field(default_factory=lambda: {
        "water": "#0066cc",
        "bunker": "#f5deb3",
        "green": "#228b22",
        "fairway": "#90ee90",
        "rough": "#556b2f",
        "cart_path": "#808080",
    })


@dataclass
class Phase2AConfig:
    """Main configuration for Phase 2A pipeline."""
    
    # Input/output paths
    input_image: Optional[Path] = None
    input_images: Optional[List[Path]] = None  # Multiple images of same topography for better accuracy
    green_centers_file: Optional[Path] = None
    output_dir: Path = field(default_factory=lambda: Path("phase2a_output"))
    
    # Sub-configurations
    thresholds: ThresholdConfig = field(default_factory=ThresholdConfig)
    sam: SAMConfig = field(default_factory=SAMConfig)
    polygon: PolygonConfig = field(default_factory=PolygonConfig)
    svg: SVGConfig = field(default_factory=SVGConfig)
    
    # Pipeline options
    skip_review: bool = True
    export_intermediates: bool = True
    verbose: bool = False
    
    def __post_init__(self):
        """Ensure paths are Path objects."""
        if self.input_image is not None:
            self.input_image = Path(self.input_image)
        if self.input_images is not None:
            self.input_images = [Path(img) for img in self.input_images]
        if self.green_centers_file is not None:
            self.green_centers_file = Path(self.green_centers_file)
        self.output_dir = Path(self.output_dir)
    
    @classmethod
    def from_yaml(cls, path: Path) -> "Phase2AConfig":
        """Load configuration from a YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls._from_dict(data)
    
    @classmethod
    def from_json(cls, path: Path) -> "Phase2AConfig":
        """Load configuration from a JSON file."""
        with open(path) as f:
            data = json.load(f)
        return cls._from_dict(data)
    
    @classmethod
    def _from_dict(cls, data: dict) -> "Phase2AConfig":
        """Create config from dictionary."""
        # Handle nested configs
        if "thresholds" in data:
            data["thresholds"] = ThresholdConfig(**data["thresholds"])
        if "sam" in data:
            data["sam"] = SAMConfig(**data["sam"])
        if "polygon" in data:
            data["polygon"] = PolygonConfig(**data["polygon"])
        if "svg" in data:
            data["svg"] = SVGConfig(**data["svg"])
        return cls(**data)
    
    def to_dict(self) -> dict:
        """Export configuration to dictionary."""
        return {
            "input_image": str(self.input_image) if self.input_image else None,
            "input_images": [str(img) for img in self.input_images] if self.input_images else None,
            "green_centers_file": str(self.green_centers_file) if self.green_centers_file else None,
            "output_dir": str(self.output_dir),
            "thresholds": {
                "high": self.thresholds.high,
                "low": self.thresholds.low,
            },
            "sam": {
                "model_type": self.sam.model_type,
                "checkpoint_path": self.sam.checkpoint_path,
                "points_per_side": self.sam.points_per_side,
                "pred_iou_thresh": self.sam.pred_iou_thresh,
                "stability_score_thresh": self.sam.stability_score_thresh,
                "min_mask_region_area": self.sam.min_mask_region_area,
            },
            "polygon": {
                "simplify_tolerance": self.polygon.simplify_tolerance,
                "min_area": self.polygon.min_area,
                "buffer_distance": self.polygon.buffer_distance,
            },
            "svg": {
                "width": self.svg.width,
                "height": self.svg.height,
                "stroke_width": self.svg.stroke_width,
                "colors": self.svg.colors,
            },
            "skip_review": self.skip_review,
            "export_intermediates": self.export_intermediates,
            "verbose": self.verbose,
        }
    
    def to_yaml(self, path: Path) -> None:
        """Save configuration to YAML file."""
        with open(path, "w") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False)
    
    def to_json(self, path: Path) -> None:
        """Save configuration to JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
