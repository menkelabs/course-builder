"""
Phase 1A Pipeline Modules

Each module corresponds to a stage in the Phase 1A pipeline:
1. masks - SAM mask generation
2. features - Mask feature extraction
3. classify - Mask classification
4. gating - Confidence gating
5. polygons - Polygon generation
6. holes - Hole assignment
7. svg - SVG generation and cleanup
8. export - PNG export
"""

from .masks import MaskGenerator
from .features import FeatureExtractor
from .classify import MaskClassifier
from .gating import ConfidenceGate
from .polygons import PolygonGenerator
from .holes import HoleAssigner
from .svg import SVGGenerator, SVGCleaner
from .export import PNGExporter
from .interactive import InteractiveSelector, HoleSelection, FeatureType
from .point_selector import PointBasedSelector

__all__ = [
    "MaskGenerator",
    "FeatureExtractor", 
    "MaskClassifier",
    "ConfidenceGate",
    "PolygonGenerator",
    "HoleAssigner",
    "SVGGenerator",
    "SVGCleaner",
    "PNGExporter",
    "InteractiveSelector",
    "HoleSelection",
    "FeatureType",
    "PointBasedSelector",
]
