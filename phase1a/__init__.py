"""
Phase 1A - Interactive tracing & SVG export (Phase 1 of roadmap).

Automatic extraction of golf course features from satellite imagery
using SAM proposals and lightweight mask classification.
"""

__version__ = "0.1.0"

from .client import Phase1AClient
from .config import Phase1AConfig

__all__ = ["Phase1AClient", "Phase1AConfig", "__version__"]
