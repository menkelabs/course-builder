"""Regions → polygons: contours, holes, Douglas–Peucker, optional smoothing."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np

from .masks import Region


@dataclass
class PolygonFeature:
    """Single polygon with class and metadata."""

    id: str
    class_name: str
    geometry: Any  # Shapely Polygon | MultiPolygon
    properties: Dict[str, Any]


def regions_to_polygons(
    regions_by_class: Dict[str, List[Region]],
    simplify_tolerance: float = 2.0,
    min_area: float = 50.0,
    smooth: bool = True,
) -> List[PolygonFeature]:
    """
    Convert regions to Shapely polygons.
    
    - Extract outer contours + holes (RETR_CCOMP or RETR_TREE).
    - Douglas–Peucker simplify, then optional smoothing.
    """
    try:
        import cv2
        from shapely.geometry import Polygon, MultiPolygon
        from shapely.validation import make_valid
    except ImportError as e:
        raise ImportError(f"opencv-python and shapely required: {e}") from e

    features: List[PolygonFeature] = []
    fid = 0

    for cname, regs in regions_by_class.items():
        for r in regs:
            m = (r.mask * 255).astype(np.uint8)
            contours, hierarchy = cv2.findContours(
                m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE
            )
            if not contours:
                continue

            polys: List[Polygon] = []
            hi = hierarchy[0] if hierarchy is not None else None

            for k, cnt in enumerate(contours):
                if len(cnt) < 3:
                    continue
                pts = cnt.reshape(-1, 2).tolist()
                try:
                    p = Polygon(pts)
                except Exception:
                    continue
                if not p.is_valid:
                    p = make_valid(p)
                if p.area < min_area:
                    continue
                # Identify holes (inner contours)
                if hi is not None and hi[k][2] >= 0:
                    continue  # has children → outer
                polys.append(p)

            if not polys:
                continue

            geom = polys[0] if len(polys) == 1 else MultiPolygon(polys)
            if not geom.is_valid:
                geom = make_valid(geom)
            if simplify_tolerance > 0:
                geom = geom.simplify(simplify_tolerance, preserve_topology=True)
            if geom.area < min_area:
                continue

            fid += 1
            features.append(
                PolygonFeature(
                    id=f"{cname}_{fid}",
                    class_name=cname,
                    geometry=geom,
                    properties={"area": geom.area, "perimeter": geom.length},
                )
            )

    return features
