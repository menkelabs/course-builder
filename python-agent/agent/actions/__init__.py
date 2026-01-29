"""
Action definitions for the Python Agent.

Actions are registered automatically when this module is imported.
Each action corresponds to a tool in the Course Builder pipeline.
"""

# Import all action modules to register them (SegFormer-focused: Phase 1A only)
from . import phase1a

__all__ = ["phase1a"]
