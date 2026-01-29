"""Tests for the data models."""

import pytest

from agent.models import (
    Io,
    PropertyDef,
    DynamicType,
    ActionMetadata,
    ActionExecutionRequest,
    ActionExecutionResponse,
    ServerRegistration,
)


class TestIo:
    """Tests for Io model."""
    
    def test_create_io(self):
        io = Io(name="input1", type="string")
        assert io.name == "input1"
        assert io.type == "string"
    
    def test_to_dict(self):
        io = Io(name="config", type="Phase1AConfig")
        result = io.to_dict()
        assert result == {"name": "config", "type": "Phase1AConfig"}


class TestPropertyDef:
    """Tests for PropertyDef model."""
    
    def test_create_property(self):
        prop = PropertyDef(
            name="satellite_image",
            type="string",
            description="Path to satellite image",
        )
        assert prop.name == "satellite_image"
        assert prop.type == "string"
        assert prop.description == "Path to satellite image"
    
    def test_to_dict(self):
        prop = PropertyDef(name="value", type="number", description="Some value")
        result = prop.to_dict()
        assert result == {
            "name": "value",
            "type": "number",
            "description": "Some value",
        }


class TestDynamicType:
    """Tests for DynamicType model."""
    
    def test_create_type(self):
        dtype = DynamicType(
            name="TestType",
            description="A test type",
            own_properties=[
                PropertyDef("field1", "string", "First field"),
                PropertyDef("field2", "number", "Second field"),
            ],
        )
        assert dtype.name == "TestType"
        assert dtype.description == "A test type"
        assert len(dtype.own_properties) == 2
    
    def test_to_dict(self):
        dtype = DynamicType(
            name="TestType",
            description="A test type",
            own_properties=[PropertyDef("field1", "string", "")],
            parents=["BaseType"],
            creation_permitted=False,
        )
        result = dtype.to_dict()
        
        assert result["name"] == "TestType"
        assert result["description"] == "A test type"
        assert len(result["ownProperties"]) == 1
        assert result["parents"] == ["BaseType"]
        assert result["creationPermitted"] is False


class TestActionMetadata:
    """Tests for ActionMetadata model."""
    
    def test_create_action(self):
        action = ActionMetadata(
            name="phase1a_run",
            description="Run Phase1A pipeline",
            inputs=[Io("config", "Phase1AConfig")],
            outputs=[Io("result", "Phase1AResult")],
            pre=["satellite_image_exists"],
            post=["svg_complete"],
            cost=0.8,
            value=0.9,
        )
        assert action.name == "phase1a_run"
        assert len(action.inputs) == 1
        assert len(action.outputs) == 1
        assert action.pre == ["satellite_image_exists"]
        assert action.post == ["svg_complete"]
    
    def test_to_dict(self):
        action = ActionMetadata(
            name="test_action",
            description="A test",
            inputs=[Io("in1", "string")],
            outputs=[Io("out1", "string")],
            pre=["pre1"],
            post=["post1"],
            cost=0.3,
            value=0.7,
            can_rerun=False,
        )
        result = action.to_dict()
        
        assert result["name"] == "test_action"
        assert result["description"] == "A test"
        assert len(result["inputs"]) == 1
        assert result["inputs"][0] == {"name": "in1", "type": "string"}
        assert result["cost"] == 0.3
        assert result["value"] == 0.7
        assert result["can_rerun"] is False


class TestActionExecutionResponse:
    """Tests for ActionExecutionResponse model."""
    
    def test_success_response(self):
        response = ActionExecutionResponse(
            result={"svg_file": "/output/course.svg"},
            status="success",
        )
        result = response.to_dict()
        
        assert result["status"] == "success"
        assert result["result"] == {"svg_file": "/output/course.svg"}
        assert "error" not in result
    
    def test_error_response(self):
        response = ActionExecutionResponse(
            result={},
            status="error",
            error="Action failed",
        )
        result = response.to_dict()
        
        assert result["status"] == "error"
        assert result["error"] == "Action failed"


class TestServerRegistration:
    """Tests for ServerRegistration model."""
    
    def test_create_registration(self):
        reg = ServerRegistration(
            base_url="http://localhost:8000",
            name="python-agent",
            description="Python tools for Course Builder",
        )
        assert reg.base_url == "http://localhost:8000"
        assert reg.name == "python-agent"
    
    def test_to_dict(self):
        reg = ServerRegistration(
            base_url="http://localhost:8000",
            name="test-agent",
            description="Test",
        )
        result = reg.to_dict()
        
        assert result["baseUrl"] == "http://localhost:8000"
        assert result["name"] == "test-agent"
        assert result["description"] == "Test"
