"""Phase 2.1 pipeline: SegFormer → masks → polygons → SVG (optional SAM 2 refine)."""

from .data import load_danish_dataset
from .dataset import DanishGolfDataset, extract_danish_archive, load_danish_from_zip
from .inference import SemanticSegmenter
from .masks import semantic_mask_to_regions, resolve_overlaps
from .polygons import regions_to_polygons, PolygonFeature

__all__ = [
    "load_danish_dataset",
    "DanishGolfDataset",
    "extract_danish_archive",
    "load_danish_from_zip",
    "SemanticSegmenter",
    "semantic_mask_to_regions",
    "resolve_overlaps",
    "regions_to_polygons",
    "PolygonFeature",
]
