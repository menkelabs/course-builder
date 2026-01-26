"""
Action definitions for the Python Agent.

Actions are registered automatically when this module is imported.
Each action corresponds to a tool in the Course Builder pipeline.
"""

# Import all action modules to register them
from . import phase2a
from . import phase1

__all__ = ["phase2a", "phase1"]
