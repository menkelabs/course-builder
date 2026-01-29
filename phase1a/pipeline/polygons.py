"""
Polygon Generation Module

Converts binary masks to clean polygon geometries.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import logging

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class PolygonFeature:
    """A polygon with its classification and metadata."""
    id: str
    feature_class: str
    confidence: float
    geometry: Any  # Shapely geometry
    properties: Dict[str, Any]
    
    def to_geojson(self) -> dict:
        """Export as GeoJSON Feature."""
        from shapely.geometry import mapping
        
        return {
            "type": "Feature",
            "id": self.id,
            "properties": {
                "class": self.feature_class,
                "confidence": self.confidence,
                **self.properties,
            },
            "geometry": mapping(self.geometry),
        }


class PolygonGenerator:
    """
    Convert masks to clean polygon geometries.
    
    Operations:
    - Extract contours from binary masks
    - Convert to Shapely polygons
    - Simplify geometry
    - Remove small artifacts
    - Fix invalid topology
    """
    
    def __init__(
        self,
        simplify_tolerance: float = 2.0,
        min_area: float = 50.0,
        buffer_distance: float = 0.0,
    ):
        """
        Initialize the polygon generator.
        
        Args:
            simplify_tolerance: Tolerance for Douglas-Peucker simplification
            min_area: Minimum polygon area to keep
            buffer_distance: Buffer distance for smoothing (0 = no buffer)
        """
        self.simplify_tolerance = simplify_tolerance
        self.min_area = min_area
        self.buffer_distance = buffer_distance
    
    def mask_to_polygon(
        self,
        mask: np.ndarray,
        mask_id: str,
        feature_class: str,
        confidence: float,
    ) -> Optional[PolygonFeature]:
        """
        Convert a binary mask to a polygon.
        
        Args:
            mask: Binary mask array (H, W)
            mask_id: Identifier for this mask
            feature_class: Classification of this mask
            confidence: Classification confidence
            
        Returns:
            PolygonFeature or None if conversion fails
        """
        try:
            import cv2
            from shapely.geometry import Polygon, MultiPolygon
            from shapely.validation import make_valid
        except ImportError as e:
            logger.error(f"Missing dependency: {e}")
            return None
        
        # Find contours
        mask_uint8 = (mask * 255).astype(np.uint8)
        contours, hierarchy = cv2.findContours(
            mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        
        if not contours:
            return None
        
        # Convert contours to polygons
        polygons = []
        for contour in contours:
            if len(contour) < 3:
                continue
            
            # Flatten contour points
            points = contour.reshape(-1, 2).tolist()
            
            if len(points) < 3:
                continue
            
            try:
                poly = Polygon(points)
                if poly.is_valid and poly.area >= self.min_area:
                    polygons.append(poly)
            except Exception as e:
                logger.debug(f"Failed to create polygon: {e}")
                continue
        
        if not polygons:
            return None
        
        # Combine into single geometry
        if len(polygons) == 1:
            geometry = polygons[0]
        else:
            geometry = MultiPolygon(polygons)
        
        # Fix invalid geometry
        if not geometry.is_valid:
            geometry = make_valid(geometry)
        
        # Simplify
        if self.simplify_tolerance > 0:
            geometry = geometry.simplify(
                self.simplify_tolerance,
                preserve_topology=True,
            )
        
        # Buffer for smoothing
        if self.buffer_distance > 0:
            geometry = geometry.buffer(self.buffer_distance)
            geometry = geometry.buffer(-self.buffer_distance)
        
        # Final area check
        if geometry.area < self.min_area:
            return None
        
        return PolygonFeature(
            id=mask_id,
            feature_class=feature_class,
            confidence=confidence,
            geometry=geometry,
            properties={
                "area": geometry.area,
                "perimeter": geometry.length,
            },
        )
    
    def generate_all(
        self,
        masks: List[Any],  # List of MaskData
        gated_masks: List[Any],  # List of GatedMask
    ) -> List[PolygonFeature]:
        """
        Generate polygons for all accepted masks.
        
        Args:
            masks: List of MaskData objects
            gated_masks: List of accepted GatedMask objects
            
        Returns:
            List of PolygonFeature objects
        """
        # Create lookup from mask_id to mask data
        mask_lookup = {m.id: m for m in masks}
        
        polygons = []
        for gated in gated_masks:
            mask_id = gated.classification.mask_id
            
            if mask_id not in mask_lookup:
                logger.warning(f"Mask {mask_id} not found in mask data")
                continue
            
            mask_data = mask_lookup[mask_id]
            
            polygon = self.mask_to_polygon(
                mask=mask_data.mask,
                mask_id=mask_id,
                feature_class=gated.classification.feature_class.value,
                confidence=gated.classification.confidence,
            )
            
            if polygon is not None:
                polygons.append(polygon)
        
        logger.info(f"Generated {len(polygons)} polygons from {len(gated_masks)} masks")
        return polygons
    
    def save_polygons(
        self,
        polygons: List[PolygonFeature],
        output_dir: Path,
    ) -> None:
        """
        Save polygons as individual GeoJSON files.
        
        Args:
            polygons: List of PolygonFeature objects
            output_dir: Directory to save polygons
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for polygon in polygons:
            geojson = polygon.to_geojson()
            output_path = output_dir / f"feature_{polygon.id}.geojson"
            
            with open(output_path, "w") as f:
                json.dump(geojson, f, indent=2)
        
        # Also save combined GeoJSON
        feature_collection = {
            "type": "FeatureCollection",
            "features": [p.to_geojson() for p in polygons],
        }
        
        with open(output_dir / "all_features.geojson", "w") as f:
            json.dump(feature_collection, f, indent=2)
        
        logger.info(f"Saved {len(polygons)} polygons to {output_dir}")
    
    @staticmethod
    def load_polygons(polygons_dir: Path) -> List[PolygonFeature]:
        """
        Load polygons from GeoJSON files.
        
        Args:
            polygons_dir: Directory containing GeoJSON files
            
        Returns:
            List of PolygonFeature objects
        """
        from shapely.geometry import shape
        
        polygons_dir = Path(polygons_dir)
        polygons = []
        
        # Try loading combined file first
        combined_path = polygons_dir / "all_features.geojson"
        if combined_path.exists():
            with open(combined_path) as f:
                fc = json.load(f)
            
            for feature in fc["features"]:
                polygon = PolygonFeature(
                    id=feature["id"],
                    feature_class=feature["properties"]["class"],
                    confidence=feature["properties"]["confidence"],
                    geometry=shape(feature["geometry"]),
                    properties={
                        k: v for k, v in feature["properties"].items()
                        if k not in ("class", "confidence")
                    },
                )
                polygons.append(polygon)
        else:
            # Load individual files
            for geojson_path in sorted(polygons_dir.glob("feature_*.geojson")):
                with open(geojson_path) as f:
                    feature = json.load(f)
                
                polygon = PolygonFeature(
                    id=feature["id"],
                    feature_class=feature["properties"]["class"],
                    confidence=feature["properties"]["confidence"],
                    geometry=shape(feature["geometry"]),
                    properties={
                        k: v for k, v in feature["properties"].items()
                        if k not in ("class", "confidence")
                    },
                )
                polygons.append(polygon)
        
        logger.info(f"Loaded {len(polygons)} polygons from {polygons_dir}")
        return polygons
