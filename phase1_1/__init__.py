"""
Phase 1.1 - SegFormer semantic segmentation pipeline

Train → deploy → masks → polygons → SVG, with optional SAM 2 edge refinement.
Uses Danish Golf Courses Orthophotos (Kaggle) for training.
"""

__version__ = "0.1.0"

from .config import Phase11Config

__all__ = ["Phase11Config", "__version__"]
