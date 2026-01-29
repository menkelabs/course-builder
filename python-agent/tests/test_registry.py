"""Tests for the action registry."""

import pytest

from agent.registry import ActionRegistry, get_registry, reset_registry
from agent.models import Io, ActionMetadata, DynamicType, PropertyDef


class TestActionRegistry:
    """Tests for ActionRegistry."""
    
    def test_create_registry(self, registry):
        """Test creating an empty registry."""
        assert len(registry.list_actions()) == 0
        assert len(registry.list_types()) == 0
    
    def test_action_decorator(self, registry):
        """Test registering an action with the decorator."""
        @registry.action(
            name="test_action",
            description="A test action",
            inputs=[Io("input1", "string")],
            outputs=[Io("output1", "string")],
        )
        async def handler(params):
            return {"output1": "result"}
        
        actions = registry.list_actions()
        assert len(actions) == 1
        assert actions[0].name == "test_action"
    
    def test_register_action_programmatic(self, registry):
        """Test registering an action programmatically."""
        metadata = ActionMetadata(
            name="prog_action",
            description="Programmatic action",
            inputs=[Io("in1", "string")],
            outputs=[Io("out1", "string")],
        )
        
        async def handler(params):
            return {"out1": "done"}
        
        registry.register_action(metadata, handler)
        
        action = registry.get_action("prog_action")
        assert action is not None
        assert action.metadata.name == "prog_action"
    
    def test_register_type(self, registry):
        """Test registering a type."""
        dtype = DynamicType(
            name="TestType",
            description="A test type",
            own_properties=[
                PropertyDef("field1", "string", "A field"),
            ],
        )
        registry.register_type(dtype)
        
        types = registry.list_types()
        assert len(types) == 1
        assert types[0].name == "TestType"
    
    def test_get_action(self, registry):
        """Test getting an action by name."""
        @registry.action(name="my_action", description="Test")
        async def handler(params):
            return {}
        
        action = registry.get_action("my_action")
        assert action is not None
        assert action.metadata.name == "my_action"
        
        missing = registry.get_action("nonexistent")
        assert missing is None
    
    def test_get_type(self, registry):
        """Test getting a type by name."""
        dtype = DynamicType(name="MyType", description="Test type")
        registry.register_type(dtype)
        
        found = registry.get_type("MyType")
        assert found is not None
        assert found.name == "MyType"
        
        missing = registry.get_type("NonexistentType")
        assert missing is None
    
    @pytest.mark.asyncio
    async def test_execute_action(self, registry):
        """Test executing an action."""
        @registry.action(
            name="echo_action",
            description="Echo action",
            inputs=[Io("message", "string")],
            outputs=[Io("echo", "string")],
        )
        async def handler(params):
            return {"echo": f"Echo: {params.get('message', '')}"}
        
        response = await registry.execute("echo_action", {"message": "Hello"})
        
        assert response.status == "success"
        assert response.result == {"echo": "Echo: Hello"}
    
    @pytest.mark.asyncio
    async def test_execute_missing_action(self, registry):
        """Test executing a non-existent action."""
        response = await registry.execute("nonexistent", {})
        
        assert response.status == "error"
        assert "not found" in response.error.lower()
    
    @pytest.mark.asyncio
    async def test_execute_action_with_error(self, registry):
        """Test executing an action that raises an error."""
        @registry.action(name="error_action", description="Fails")
        async def handler(params):
            raise ValueError("Something went wrong")
        
        response = await registry.execute("error_action", {})
        
        assert response.status == "error"
        assert "Something went wrong" in response.error


class TestGlobalRegistry:
    """Tests for global registry functions."""
    
    def test_get_registry(self):
        """Test getting the global registry."""
        reset_registry()
        reg1 = get_registry()
        reg2 = get_registry()
        
        assert reg1 is reg2  # Same instance
    
    def test_reset_registry(self):
        """Test resetting the global registry."""
        reset_registry()
        reg1 = get_registry()
        
        @reg1.action(name="temp_action", description="Temp")
        async def handler(params):
            return {}
        
        assert len(reg1.list_actions()) == 1
        
        reset_registry()
        reg2 = get_registry()
        
        assert reg1 is not reg2
        assert len(reg2.list_actions()) == 0
