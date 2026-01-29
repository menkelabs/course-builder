"""Semantic mask → per-class regions with overlap resolution."""

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np

from ..config import PRIORITY_ORDER


@dataclass
class Region:
    """Single connected component of a class."""

    class_name: str
    mask: np.ndarray  # binary H×W
    bbox: Tuple[int, int, int, int]  # x, y, w, h


def semantic_mask_to_regions(
    mask: np.ndarray,
    class_map: Dict[int, str],
    min_area: int = 50,
) -> Dict[str, List[Region]]:
    """
    Extract one polygon per connected component per class.
    
    Returns {class_name: [Region, ...]}.
    """
    import cv2
    from scipy import ndimage

    h, w = mask.shape
    out: Dict[str, List[Region]] = {}

    for cid, cname in class_map.items():
        if cname == "background" or cid == 0:
            continue
        binary = (mask == cid).astype(np.uint8)
        if binary.sum() < min_area:
            continue
        labeled, n = ndimage.label(binary)
        for idx in range(1, n + 1):
            comp = (labeled == idx).astype(np.uint8)
            if comp.sum() < min_area:
                continue
            ys, xs = np.where(comp)
            x0, y0 = int(xs.min()), int(ys.min())
            x1, y1 = int(xs.max()), int(ys.max())
            out.setdefault(cname, []).append(
                Region(class_name=cname, mask=comp.astype(bool), bbox=(x0, y0, x1 - x0 + 1, y1 - y0 + 1))
            )

    return out


def resolve_overlaps(
    regions_by_class: Dict[str, List[Region]],
    priority: List[str],
    height: int,
    width: int,
) -> Dict[str, List[Region]]:
    """
    Enforce priority order: subtract higher-priority masks from lower-priority
    before polygonizing. water > bunker > green > tee > fairway > background.
    """
    import cv2

    # Build cumulative higher-priority mask per class
    acc = np.zeros((height, width), dtype=np.uint8)
    ordered = [c for c in priority if c in regions_by_class]

    result: Dict[str, List[Region]] = {}

    for cname in ordered:
        regs = regions_by_class[cname]
        for r in regs:
            m = r.mask.astype(np.uint8)
            subtracted = np.clip(m.astype(np.int32) - acc, 0, 1).astype(np.uint8)
            if subtracted.sum() < 50:
                continue
            ys, xs = np.where(subtracted > 0)
            x0, y0 = int(xs.min()), int(ys.min())
            x1, y1 = int(xs.max()), int(ys.max())
            result.setdefault(cname, []).append(
                Region(
                    class_name=cname,
                    mask=subtracted.astype(bool),
                    bbox=(x0, y0, x1 - x0 + 1, y1 - y0 + 1),
                )
            )
        # Add this class to accumulator
        for r in regs:
            acc = np.maximum(acc, r.mask.astype(np.uint8))

    return result
