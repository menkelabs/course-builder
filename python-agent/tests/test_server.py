"""Tests for the FastAPI server endpoints."""

import pytest
from fastapi.testclient import TestClient

from agent.server import create_app
from agent.registry import ActionRegistry
from agent.models import Io, DynamicType, PropertyDef


class TestRootEndpoints:
    """Tests for root and health endpoints."""
    
    def test_root(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        
        assert "name" in data
        assert "version" in data
        assert "endpoints" in data
    
    def test_health(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestActionsEndpoint:
    """Tests for /api/v1/actions endpoint."""
    
    def test_list_actions_empty(self, client):
        """Test listing actions with empty registry."""
        response = client.get("/api/v1/actions")
        assert response.status_code == 200
        assert response.json() == []
    
    def test_list_actions_populated(self, populated_client):
        """Test listing actions with populated registry."""
        response = populated_client.get("/api/v1/actions")
        assert response.status_code == 200
        
        actions = response.json()
        assert len(actions) == 1
        assert actions[0]["name"] == "test_action"
        assert actions[0]["description"] == "A test action"
        assert len(actions[0]["inputs"]) == 1
        assert len(actions[0]["outputs"]) == 1
    
    def test_get_specific_action(self, populated_client):
        """Test getting a specific action."""
        response = populated_client.get("/api/v1/actions/test_action")
        assert response.status_code == 200
        
        action = response.json()
        assert action["name"] == "test_action"
    
    def test_get_missing_action(self, populated_client):
        """Test getting a non-existent action."""
        response = populated_client.get("/api/v1/actions/nonexistent")
        assert response.status_code == 404


class TestTypesEndpoint:
    """Tests for /api/v1/types endpoint."""
    
    def test_list_types_empty(self, client, registry):
        """Test listing types with empty registry."""
        response = client.get("/api/v1/types")
        assert response.status_code == 200
        assert response.json() == []
    
    def test_list_types_populated(self, client, registry):
        """Test listing types with registered types."""
        dtype = DynamicType(
            name="TestType",
            description="A test type",
            own_properties=[
                PropertyDef("field1", "string", "A field"),
            ],
        )
        registry.register_type(dtype)
        
        response = client.get("/api/v1/types")
        assert response.status_code == 200
        
        types = response.json()
        assert len(types) == 1
        assert types[0]["name"] == "TestType"
        assert len(types[0]["ownProperties"]) == 1


class TestExecuteEndpoint:
    """Tests for /api/v1/actions/execute endpoint."""
    
    def test_execute_action(self, populated_client):
        """Test executing an action."""
        response = populated_client.post(
            "/api/v1/actions/execute",
            json={
                "action_name": "test_action",
                "parameters": {"input1": "hello"},
            },
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        assert data["result"]["output1"] == "processed: hello"
    
    def test_execute_missing_action(self, populated_client):
        """Test executing a non-existent action."""
        response = populated_client.post(
            "/api/v1/actions/execute",
            json={
                "action_name": "nonexistent",
                "parameters": {},
            },
        )
        assert response.status_code == 404
    
    def test_execute_with_empty_params(self, populated_client):
        """Test executing an action without parameters."""
        response = populated_client.post(
            "/api/v1/actions/execute",
            json={
                "action_name": "test_action",
                "parameters": {},
            },
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        assert data["result"]["output1"] == "processed: none"


class TestPhase2AActionsIntegration:
    """Integration tests for Phase2A actions."""
    
    @pytest.fixture
    def phase2a_client(self):
        """Create a client with Phase2A actions registered."""
        import importlib
        from agent.registry import reset_registry, get_registry
        
        reset_registry()
        
        # Import and reload phase2a actions to re-register them
        import agent.actions.phase2a as phase2a_module
        importlib.reload(phase2a_module)
        
        registry = get_registry()
        app = create_app(registry)
        return TestClient(app)
    
    def test_list_phase2a_actions(self, phase2a_client):
        """Test that Phase2A actions are listed."""
        response = phase2a_client.get("/api/v1/actions")
        assert response.status_code == 200
        
        actions = response.json()
        action_names = [a["name"] for a in actions]
        
        # Check for expected Phase2A actions
        assert "phase2a_run" in action_names
        assert "phase2a_generate_masks" in action_names
        assert "phase2a_classify" in action_names
        assert "phase2a_validate" in action_names
    
    def test_list_phase2a_types(self, phase2a_client):
        """Test that Phase2A types are listed."""
        response = phase2a_client.get("/api/v1/types")
        assert response.status_code == 200
        
        types = response.json()
        type_names = [t["name"] for t in types]
        
        # Check for expected types
        assert "Phase2AConfig" in type_names
        assert "Phase2AResult" in type_names
    
    def test_execute_phase2a_validate(self, phase2a_client, tmp_path):
        """Test executing phase2a_validate action."""
        # Create a minimal output directory
        output_dir = tmp_path / "phase2a_output"
        output_dir.mkdir()
        
        response = phase2a_client.post(
            "/api/v1/actions/execute",
            json={
                "action_name": "phase2a_validate",
                "parameters": {"output_dir": str(output_dir)},
            },
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        assert "valid" in data["result"]
        assert "checks" in data["result"]
