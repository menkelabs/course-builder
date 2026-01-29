"""
Hole Assignment Module

Assigns polygons to golf course holes based on spatial relationships.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging

import numpy as np

from .polygons import PolygonFeature

logger = logging.getLogger(__name__)


@dataclass
class GreenCenter:
    """A green center point for a hole."""
    hole: int
    x: float
    y: float


@dataclass
class HoleAssignment:
    """A polygon with its assigned hole number."""
    polygon: PolygonFeature
    hole: int
    distance_to_green: Optional[float] = None
    
    def to_dict(self) -> dict:
        """Export to dictionary."""
        return {
            "polygon_id": self.polygon.id,
            "feature_class": self.polygon.feature_class,
            "hole": self.hole,
            "distance_to_green": self.distance_to_green,
        }


class HoleAssigner:
    """
    Assign polygons to golf course holes.
    
    Uses:
    - Nearest green center (primary method)
    - Spatial clustering fallback
    
    Each polygon belongs to exactly one hole.
    Special holes:
    - Hole 98: Cart paths
    - Hole 99: Outer mesh / course boundary
    """
    
    CART_PATH_HOLE = 98
    OUTER_MESH_HOLE = 99
    
    def __init__(
        self,
        green_centers: Optional[List[Dict]] = None,
        max_distance: float = 1000.0,
    ):
        """
        Initialize the hole assigner.
        
        Args:
            green_centers: List of green centers [{hole, x, y}, ...]
            max_distance: Maximum distance from green center for assignment
        """
        self.green_centers = []
        if green_centers:
            for gc in green_centers:
                self.green_centers.append(GreenCenter(
                    hole=gc["hole"],
                    x=gc["x"],
                    y=gc["y"],
                ))
        
        self.max_distance = max_distance
    
    def _get_polygon_centroid(self, polygon: PolygonFeature) -> Tuple[float, float]:
        """Get centroid of a polygon."""
        centroid = polygon.geometry.centroid
        return (centroid.x, centroid.y)
    
    def _find_nearest_green(
        self,
        polygon: PolygonFeature,
    ) -> Tuple[Optional[int], Optional[float]]:
        """
        Find the nearest green center to a polygon.
        
        Returns:
            Tuple of (hole_number, distance) or (None, None) if none found
        """
        if not self.green_centers:
            return None, None
        
        centroid = self._get_polygon_centroid(polygon)
        
        min_distance = float("inf")
        nearest_hole = None
        
        for gc in self.green_centers:
            distance = np.sqrt(
                (centroid[0] - gc.x) ** 2 +
                (centroid[1] - gc.y) ** 2
            )
            
            if distance < min_distance:
                min_distance = distance
                nearest_hole = gc.hole
        
        if min_distance <= self.max_distance:
            return nearest_hole, min_distance
        
        return None, None
    
    def assign(self, polygon: PolygonFeature) -> HoleAssignment:
        """
        Assign a single polygon to a hole.
        
        Args:
            polygon: PolygonFeature to assign
            
        Returns:
            HoleAssignment with hole number
        """
        feature_class = polygon.feature_class
        
        # Cart paths go to hole 98
        if feature_class == "cart_path":
            return HoleAssignment(
                polygon=polygon,
                hole=self.CART_PATH_HOLE,
            )
        
        # Very large polygons might be course boundaries
        if polygon.geometry.area > 1000000:  # Arbitrary threshold
            return HoleAssignment(
                polygon=polygon,
                hole=self.OUTER_MESH_HOLE,
            )
        
        # Try nearest green center
        hole, distance = self._find_nearest_green(polygon)
        
        if hole is not None:
            return HoleAssignment(
                polygon=polygon,
                hole=hole,
                distance_to_green=distance,
            )
        
        # Fallback: assign to outer mesh
        logger.warning(
            f"Could not assign polygon {polygon.id} to a hole, "
            f"using outer mesh (hole {self.OUTER_MESH_HOLE})"
        )
        return HoleAssignment(
            polygon=polygon,
            hole=self.OUTER_MESH_HOLE,
        )
    
    def assign_all(
        self,
        polygons: List[PolygonFeature],
    ) -> Dict[int, List[HoleAssignment]]:
        """
        Assign all polygons to holes.
        
        Args:
            polygons: List of PolygonFeature objects
            
        Returns:
            Dictionary mapping hole numbers to lists of HoleAssignments
        """
        assignments_by_hole: Dict[int, List[HoleAssignment]] = {}
        
        for polygon in polygons:
            assignment = self.assign(polygon)
            hole = assignment.hole
            
            if hole not in assignments_by_hole:
                assignments_by_hole[hole] = []
            
            assignments_by_hole[hole].append(assignment)
        
        # Log summary
        for hole in sorted(assignments_by_hole.keys()):
            count = len(assignments_by_hole[hole])
            logger.info(f"Hole {hole:02d}: {count} features")
        
        return assignments_by_hole
    
    def save_assignments(
        self,
        assignments_by_hole: Dict[int, List[HoleAssignment]],
        output_path: Path,
    ) -> None:
        """
        Save hole assignments to JSON file.
        
        Args:
            assignments_by_hole: Dictionary of assignments
            output_path: Path to save JSON
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {}
        for hole, assignments in assignments_by_hole.items():
            data[str(hole)] = [a.to_dict() for a in assignments]
        
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved hole assignments to {output_path}")
    
    @staticmethod
    def load_green_centers(path: Path) -> List[Dict]:
        """
        Load green centers from JSON file.
        
        Expected format:
        [
            {"hole": 1, "x": 1234, "y": 567},
            {"hole": 2, "x": 1320, "y": 610}
        ]
        """
        with open(path) as f:
            return json.load(f)
