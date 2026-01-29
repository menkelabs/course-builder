"""
Python Agent for Course Builder

A Python-based agent that exposes Phase 1A and other pipeline tools
as remote actions following the embabel-agent-remote REST API pattern.

This enables Python tools to participate in the Embabel agent platform's
GOAP planning and execution.

Endpoints:
- GET /api/v1/actions - List available actions
- GET /api/v1/types - List domain types
- POST /api/v1/actions/execute - Execute an action
- POST /api/v1/remote/register - Register with Embabel server
"""

__version__ = "0.1.0"

from .models import ActionMetadata, DynamicType, Io, ActionExecutionRequest
from .registry import ActionRegistry
from .server import create_app

__all__ = [
    "ActionMetadata",
    "DynamicType", 
    "Io",
    "ActionExecutionRequest",
    "ActionRegistry",
    "create_app",
]
