"""Tests for action implementations."""

import pytest
from pathlib import Path
import importlib
from unittest.mock import patch

from agent.registry import get_registry, reset_registry


class TestPhase1AActions:
    """Tests for Phase 1A actions."""
    
    @pytest.fixture
    def registry(self):
        """Get registry with Phase 1A actions."""
        reset_registry()
        # Need to reload the module to re-register actions
        import agent.actions.phase1a as phase1a_module
        importlib.reload(phase1a_module)
        return get_registry()
    
    @pytest.mark.asyncio
    async def test_phase1a_run_mock(self, registry):
        """Test phase1a_run returns mock result when Phase 1A not available."""
        with patch("agent.actions.phase1a._get_phase1a_client", return_value=None):
            response = await registry.execute(
                "phase1a_run",
                {
                    "satellite_image": "/test/satellite.png",
                    "checkpoint": "/test/sam.pth",
                    "output_dir": "/test/output/",
                },
            )
        assert response.status == "success"
        assert "svg_file" in response.result
        assert "masks_generated" in response.result
        assert "features_classified" in response.result

    @pytest.mark.asyncio
    async def test_phase1a_generate_masks_mock(self, registry):
        """Test phase1a_generate_masks returns mock result."""
        with patch("agent.actions.phase1a._get_phase1a_client", return_value=None):
            response = await registry.execute(
                "phase1a_generate_masks",
                {
                    "satellite_image": "/test/satellite.png",
                    "checkpoint": "/test/sam.pth",
                    "output_dir": "/test/masks/",
                },
            )
        assert response.status == "success"
        assert "masks_dir" in response.result
        assert "mask_count" in response.result

    @pytest.mark.asyncio
    async def test_phase1a_classify_mock(self, registry):
        """Test phase1a_classify returns mock result."""
        with patch("agent.actions.phase1a._get_phase1a_client", return_value=None):
            response = await registry.execute(
                "phase1a_classify",
                {
                    "masks_dir": "/test/masks/",
                    "satellite_image": "/test/satellite.png",
                },
            )
        assert response.status == "success"
        assert "counts" in response.result
        assert "green" in response.result["counts"]

    @pytest.mark.asyncio
    async def test_phase1a_generate_svg_mock(self, registry):
        """Test phase1a_generate_svg returns mock result."""
        with patch("agent.actions.phase1a._get_phase1a_client", return_value=None):
            response = await registry.execute(
                "phase1a_generate_svg",
                {
                    "output_dir": "/test/output/",
                    "include_hole_98": True,
                    "include_hole_99": True,
                },
            )
        assert response.status == "success"
        assert "svg_file" in response.result
        assert "hole_layers" in response.result
        assert response.result["hole_layers"] == 20  # 18 + 2
    
    @pytest.mark.asyncio
    async def test_phase1a_validate(self, registry, tmp_path):
        """Test phase1a_validate with actual directory."""
        # Create test directory structure
        output_dir = tmp_path / "phase1a_output"
        output_dir.mkdir()
        
        # Create some files
        (output_dir / "course.svg").write_text("<svg></svg>")
        exports_dir = output_dir / "exports"
        exports_dir.mkdir()
        (exports_dir / "overlay.png").write_bytes(b"\x89PNG")
        
        metadata_dir = output_dir / "metadata"
        metadata_dir.mkdir()
        (metadata_dir / "classifications.json").write_text("[]")
        (metadata_dir / "hole_assignments.json").write_text("{}")
        
        response = await registry.execute(
            "phase1a_validate",
            {"output_dir": str(output_dir)},
        )
        
        assert response.status == "success"
        assert "valid" in response.result
        assert "checks" in response.result
    
    @pytest.mark.asyncio
    async def test_phase1a_validate_missing_files(self, registry, tmp_path):
        """Test phase1a_validate with missing files."""
        # Empty directory
        output_dir = tmp_path / "empty_output"
        output_dir.mkdir()
        
        response = await registry.execute(
            "phase1a_validate",
            {"output_dir": str(output_dir)},
        )
        
        assert response.status == "success"
        assert response.result["valid"] is False
        assert len(response.result["errors"]) > 0


class TestActionMetadata:
    """Tests for action metadata correctness."""
    
    @pytest.fixture
    def registry(self):
        """Get registry with all actions (Phase 1A only)."""
        reset_registry()
        import agent.actions.phase1a as phase1a_module
        importlib.reload(phase1a_module)
        return get_registry()
    
    def test_all_actions_have_descriptions(self, registry):
        """Test that all actions have descriptions."""
        for action in registry.list_actions():
            assert action.description, f"Action {action.name} missing description"
            assert len(action.description) > 10, f"Action {action.name} has short description"
    
    def test_all_actions_have_valid_cost_value(self, registry):
        """Test that all actions have valid cost/value."""
        for action in registry.list_actions():
            assert 0.0 <= action.cost <= 1.0, f"Action {action.name} has invalid cost"
            assert 0.0 <= action.value <= 1.0, f"Action {action.name} has invalid value"
    
    def test_phase1a_actions_have_preconditions(self, registry):
        """Test that Phase 1A actions have appropriate pre/post conditions."""
        phase1a_actions = [a for a in registry.list_actions() if a.name.startswith("phase1a_")]
        
        # phase1a_run should have svg_complete as postcondition
        run_action = next((a for a in phase1a_actions if a.name == "phase1a_run"), None)
        assert run_action is not None
        assert "svg_complete" in run_action.post
        
        # phase1a_validate should also produce svg_complete
        validate_action = next((a for a in phase1a_actions if a.name == "phase1a_validate"), None)
        assert validate_action is not None
        assert "svg_complete" in validate_action.post
