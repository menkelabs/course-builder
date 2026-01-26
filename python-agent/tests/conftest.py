"""Pytest configuration and fixtures for Python Agent tests."""

import pytest
from fastapi.testclient import TestClient

from agent.registry import ActionRegistry, reset_registry
from agent.server import create_app


@pytest.fixture
def registry():
    """Create a fresh registry for each test."""
    reset_registry()
    return ActionRegistry()


@pytest.fixture
def app(registry):
    """Create a FastAPI app with a test registry."""
    return create_app(registry)


@pytest.fixture
def client(app):
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def populated_registry(registry):
    """Create a registry populated with test actions."""
    from agent.models import Io
    
    @registry.action(
        name="test_action",
        description="A test action",
        inputs=[Io("input1", "string")],
        outputs=[Io("output1", "string")],
        pre=["condition1"],
        post=["condition2"],
        cost=0.5,
        value=0.8,
    )
    async def test_handler(params):
        return {"output1": f"processed: {params.get('input1', 'none')}"}
    
    return registry


@pytest.fixture
def populated_app(populated_registry):
    """Create a FastAPI app with populated registry."""
    return create_app(populated_registry)


@pytest.fixture
def populated_client(populated_app):
    """Create a test client with populated registry."""
    return TestClient(populated_app)
