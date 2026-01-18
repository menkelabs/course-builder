"""
Tests for the main Phase2A client.
"""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import numpy as np
import pytest

from phase2a.client import Phase2AClient, PipelineStage, PipelineState
from phase2a.config import Phase2AConfig


class TestPipelineState:
    """Tests for PipelineState dataclass."""
    
    def test_default_state(self):
        state = PipelineState()
        
        assert state.image is None
        assert state.masks == []
        assert state.features == []
        assert state.classifications == []
        assert state.accepted == []
        assert state.polygons == []
        assert state.assignments_by_hole == {}
        assert state.svg_content is None
        assert state.completed_stages == []


class TestPipelineStage:
    """Tests for PipelineStage enum."""
    
    def test_all_stages_exist(self):
        assert PipelineStage.MASKS == "masks"
        assert PipelineStage.FEATURES == "features"
        assert PipelineStage.CLASSIFY == "classify"
        assert PipelineStage.GATE == "gate"
        assert PipelineStage.POLYGONS == "polygons"
        assert PipelineStage.HOLES == "holes"
        assert PipelineStage.SVG == "svg"
        assert PipelineStage.CLEANUP == "cleanup"
        assert PipelineStage.EXPORT == "export"


class TestPhase2AClient:
    """Tests for Phase2AClient class."""
    
    def test_init_default(self):
        client = Phase2AClient()
        
        assert client.config is not None
        assert isinstance(client.state, PipelineState)
    
    def test_init_with_config(self, temp_dir):
        config = Phase2AConfig(
            output_dir=temp_dir / "output",
            verbose=True,
        )
        client = Phase2AClient(config)
        
        assert client.config.output_dir == temp_dir / "output"
        assert client.config.verbose is True
    
    def test_output_dir_created(self, temp_dir):
        config = Phase2AConfig(output_dir=temp_dir / "new_output")
        client = Phase2AClient(config)
        
        # Access output_dir property
        out = client.output_dir
        
        assert out.exists()
    
    def test_reset(self, temp_dir):
        config = Phase2AConfig(output_dir=temp_dir)
        client = Phase2AClient(config)
        
        # Add some state
        client.state.masks = [MagicMock()]
        client.state.completed_stages = [PipelineStage.MASKS]
        
        # Reset
        client.reset()
        
        assert client.state.masks == []
        assert client.state.completed_stages == []


class TestPhase2AClientPipelineStages:
    """Tests for individual pipeline stages."""
    
    def test_generate_masks_requires_image(self):
        """generate_masks should fail without input image."""
        config = Phase2AConfig()  # No input image
        client = Phase2AClient(config)
        
        with pytest.raises(ValueError, match="No input image"):
            client.generate_masks()
    
    def test_extract_features_requires_masks(self, sample_image_file, temp_dir):
        """extract_features should fail without masks."""
        config = Phase2AConfig(
            input_image=sample_image_file,
            output_dir=temp_dir,
        )
        client = Phase2AClient(config)
        
        with pytest.raises(ValueError, match="No masks available"):
            client.extract_features()
    
    def test_classify_masks_requires_features(self, temp_dir):
        config = Phase2AConfig(output_dir=temp_dir)
        client = Phase2AClient(config)
        
        with pytest.raises(ValueError, match="No features available"):
            client.classify_masks()
    
    def test_gate_masks_requires_classifications(self, temp_dir):
        config = Phase2AConfig(output_dir=temp_dir)
        client = Phase2AClient(config)
        
        with pytest.raises(ValueError, match="No classifications available"):
            client.gate_masks()
    
    def test_generate_polygons_requires_accepted(self, temp_dir):
        config = Phase2AConfig(output_dir=temp_dir)
        client = Phase2AClient(config)
        
        with pytest.raises(ValueError, match="No accepted masks"):
            client.generate_polygons()
    
    def test_assign_holes_requires_polygons(self, temp_dir):
        config = Phase2AConfig(output_dir=temp_dir)
        client = Phase2AClient(config)
        
        with pytest.raises(ValueError, match="No polygons available"):
            client.assign_holes()
    
    def test_generate_svg_requires_assignments(self, temp_dir):
        config = Phase2AConfig(output_dir=temp_dir)
        client = Phase2AClient(config)
        
        with pytest.raises(ValueError, match="No hole assignments"):
            client.generate_svg()
    
    def test_export_png_requires_svg(self, temp_dir):
        config = Phase2AConfig(output_dir=temp_dir)
        client = Phase2AClient(config)
        
        with pytest.raises(ValueError, match="No SVG content"):
            client.export_png()


class TestPhase2AClientIntegration:
    """Integration tests for Phase2AClient (without SAM)."""
    
    def test_partial_pipeline_with_mock_masks(
        self, sample_image_file, temp_dir, mock_mask_data
    ):
        """Test pipeline stages after mask generation."""
        config = Phase2AConfig(
            input_image=sample_image_file,
            output_dir=temp_dir,
            export_intermediates=True,
        )
        config.thresholds.high = 0.3  # Lower threshold for test data
        config.thresholds.low = 0.1
        
        client = Phase2AClient(config)
        
        # Inject pre-generated masks
        client.state.masks = mock_mask_data
        client.state.completed_stages.append(PipelineStage.MASKS)
        
        # Run remaining stages
        features = client.extract_features()
        assert len(features) > 0
        assert PipelineStage.FEATURES in client.state.completed_stages
        
        classifications = client.classify_masks()
        assert len(classifications) > 0
        assert PipelineStage.CLASSIFY in client.state.completed_stages
        
        accepted, review, discarded = client.gate_masks()
        assert PipelineStage.GATE in client.state.completed_stages
        
        # Only continue if we have accepted masks
        if accepted:
            polygons = client.generate_polygons()
            assert PipelineStage.POLYGONS in client.state.completed_stages
            
            if polygons:
                assignments = client.assign_holes()
                assert PipelineStage.HOLES in client.state.completed_stages
                
                svg = client.generate_svg()
                assert svg is not None
                assert PipelineStage.SVG in client.state.completed_stages
    
    def test_validate_incomplete(self, temp_dir):
        """Test validation on incomplete output."""
        config = Phase2AConfig(output_dir=temp_dir)
        client = Phase2AClient(config)
        
        # Should fail validation
        result = client.validate()
        assert result is False
    
    def test_load_masks(self, temp_dir, mock_mask_data):
        """Test loading masks from a previous run."""
        from phase2a.pipeline.masks import MaskGenerator
        
        # Save masks first
        masks_dir = temp_dir / "masks"
        generator = MaskGenerator()
        generator.save_masks(mock_mask_data, masks_dir)
        
        # Load with client
        config = Phase2AConfig(output_dir=temp_dir)
        client = Phase2AClient(config)
        
        loaded = client.load_masks(masks_dir)
        
        assert len(loaded) == len(mock_mask_data)
    
    def test_load_features(self, temp_dir, mock_features):
        """Test loading features from a previous run."""
        from phase2a.pipeline.features import FeatureExtractor
        
        # Save features first
        features_path = temp_dir / "features.json"
        extractor = FeatureExtractor()
        extractor.save_features(mock_features, features_path)
        
        # Load with client
        config = Phase2AConfig(output_dir=temp_dir)
        client = Phase2AClient(config)
        
        loaded = client.load_features(features_path)
        
        assert len(loaded) == len(mock_features)


class TestPhase2AClientConfig:
    """Tests for client configuration handling."""
    
    def test_load_green_centers(self, green_centers_file, temp_dir):
        config = Phase2AConfig(
            green_centers_file=green_centers_file,
            output_dir=temp_dir,
        )
        client = Phase2AClient(config)
        
        centers = client._load_green_centers()
        
        assert centers is not None
        assert len(centers) == 3
    
    def test_load_green_centers_missing_file(self, temp_dir):
        config = Phase2AConfig(
            green_centers_file=temp_dir / "nonexistent.json",
            output_dir=temp_dir,
        )
        client = Phase2AClient(config)
        
        centers = client._load_green_centers()
        
        assert centers is None
    
    def test_load_green_centers_no_file(self, temp_dir):
        config = Phase2AConfig(output_dir=temp_dir)
        client = Phase2AClient(config)
        
        centers = client._load_green_centers()
        
        assert centers is None
    
    def test_verbose_logging(self, temp_dir):
        config = Phase2AConfig(
            output_dir=temp_dir,
            verbose=True,
        )
        
        # Should not raise
        client = Phase2AClient(config)
