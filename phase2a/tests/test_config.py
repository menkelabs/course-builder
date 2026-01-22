"""
Tests for configuration module.
"""

import json
from pathlib import Path

import pytest
import yaml

from phase2a.config import (
    Phase2AConfig,
    ThresholdConfig,
    SAMConfig,
    PolygonConfig,
    SVGConfig,
)


class TestThresholdConfig:
    """Tests for ThresholdConfig."""
    
    def test_default_values(self):
        config = ThresholdConfig()
        assert config.high == 0.85
        assert config.low == 0.5
    
    def test_custom_values(self):
        config = ThresholdConfig(high=0.9, low=0.3)
        assert config.high == 0.9
        assert config.low == 0.3


class TestSAMConfig:
    """Tests for SAMConfig."""
    
    def test_default_values(self):
        config = SAMConfig()
        assert config.model_type == "vit_h"
        assert config.checkpoint_path is None
        assert config.points_per_side == 32
        assert config.pred_iou_thresh == 0.88
        assert config.stability_score_thresh == 0.95
        assert config.min_mask_region_area == 100
    
    def test_custom_values(self):
        config = SAMConfig(
            model_type="vit_l",
            checkpoint_path="/path/to/model.pth",
            points_per_side=64,
        )
        assert config.model_type == "vit_l"
        assert config.checkpoint_path == "/path/to/model.pth"
        assert config.points_per_side == 64


class TestPolygonConfig:
    """Tests for PolygonConfig."""
    
    def test_default_values(self):
        config = PolygonConfig()
        assert config.simplify_tolerance == 2.0
        assert config.min_area == 50.0
        assert config.buffer_distance == 0.0


class TestSVGConfig:
    """Tests for SVGConfig."""
    
    def test_default_values(self):
        config = SVGConfig()
        assert config.width == 4096
        assert config.height == 4096
        assert config.opacity == 0.5
        assert "water" in config.colors
        assert "bunker" in config.colors
        assert "green" in config.colors
    
    def test_colors_are_valid_hex(self):
        config = SVGConfig()
        for color in config.colors.values():
            assert color.startswith("#")
            assert len(color) == 7


class TestPhase2AConfig:
    """Tests for main Phase2AConfig."""
    
    def test_default_values(self):
        config = Phase2AConfig()
        assert config.input_image is None
        assert config.green_centers_file is None
        assert config.output_dir == Path("phase2a_output")
        assert config.skip_review is True
        assert config.export_intermediates is True
        assert config.verbose is False
    
    def test_path_conversion(self):
        config = Phase2AConfig(
            input_image="test.png",
            output_dir="output",
        )
        assert isinstance(config.input_image, Path)
        assert isinstance(config.output_dir, Path)
    
    def test_to_dict(self):
        config = Phase2AConfig(
            input_image="test.png",
            output_dir="output",
        )
        data = config.to_dict()
        
        assert data["input_image"] == "test.png"
        assert data["output_dir"] == "output"
        assert "thresholds" in data
        assert "sam" in data
        assert "polygon" in data
        assert "svg" in data
    
    def test_to_yaml(self, temp_dir):
        config = Phase2AConfig(
            input_image="test.png",
            output_dir="output",
        )
        yaml_path = temp_dir / "config.yaml"
        config.to_yaml(yaml_path)
        
        assert yaml_path.exists()
        
        with open(yaml_path) as f:
            data = yaml.safe_load(f)
        
        assert data["input_image"] == "test.png"
    
    def test_to_json(self, temp_dir):
        config = Phase2AConfig(
            input_image="test.png",
            output_dir="output",
        )
        json_path = temp_dir / "config.json"
        config.to_json(json_path)
        
        assert json_path.exists()
        
        with open(json_path) as f:
            data = json.load(f)
        
        assert data["input_image"] == "test.png"
    
    def test_from_yaml(self, temp_dir):
        yaml_path = temp_dir / "config.yaml"
        data = {
            "input_image": "satellite.png",
            "output_dir": "results",
            "thresholds": {"high": 0.9, "low": 0.4},
            "verbose": True,
        }
        with open(yaml_path, "w") as f:
            yaml.dump(data, f)
        
        config = Phase2AConfig.from_yaml(yaml_path)
        
        assert config.input_image == Path("satellite.png")
        assert config.output_dir == Path("results")
        assert config.thresholds.high == 0.9
        assert config.thresholds.low == 0.4
        assert config.verbose is True
    
    def test_from_json(self, temp_dir):
        json_path = temp_dir / "config.json"
        data = {
            "input_image": "satellite.png",
            "output_dir": "results",
            "sam": {"model_type": "vit_l", "points_per_side": 64},
        }
        with open(json_path, "w") as f:
            json.dump(data, f)
        
        config = Phase2AConfig.from_json(json_path)
        
        assert config.input_image == Path("satellite.png")
        assert config.sam.model_type == "vit_l"
        assert config.sam.points_per_side == 64
