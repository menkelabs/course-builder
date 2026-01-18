"""
Phase 2A - Automated Satellite Tracing

Automatic extraction of golf course features from satellite imagery
using SAM proposals and lightweight mask classification.
"""

__version__ = "0.1.0"

from .client import Phase2AClient
from .config import Phase2AConfig

__all__ = ["Phase2AClient", "Phase2AConfig", "__version__"]
