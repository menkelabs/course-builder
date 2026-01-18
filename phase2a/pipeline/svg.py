"""
SVG Generation Module

Generates structured SVG files with per-hole layers and OPCD color classes.
"""

import json
from pathlib import Path
from typing import List, Dict, Optional, Any
import logging

from .holes import HoleAssignment

logger = logging.getLogger(__name__)


class SVGGenerator:
    """
    Generate course SVG with structured layers.
    
    Layers:
    - Hole01 through Hole18
    - Hole98_CartPaths
    - Hole99_OuterMesh
    
    Classes (OPCD palette):
    - .water
    - .bunker
    - .green
    - .fairway
    - .rough
    """
    
    # OPCD color palette
    DEFAULT_COLORS = {
        "water": "#0066cc",
        "bunker": "#f5deb3",
        "green": "#228b22",
        "fairway": "#90ee90",
        "rough": "#556b2f",
        "cart_path": "#808080",
        "ignore": "#cccccc",
    }
    
    def __init__(
        self,
        width: int = 4096,
        height: int = 4096,
        colors: Optional[Dict[str, str]] = None,
        stroke_width: float = 1.0,
    ):
        """
        Initialize the SVG generator.
        
        Args:
            width: SVG width in pixels
            height: SVG height in pixels
            colors: Custom color palette (overrides defaults)
            stroke_width: Stroke width for paths
        """
        self.width = width
        self.height = height
        self.colors = {**self.DEFAULT_COLORS, **(colors or {})}
        self.stroke_width = stroke_width
    
    def _polygon_to_path(self, geometry: Any) -> str:
        """
        Convert a Shapely geometry to SVG path data.
        
        Args:
            geometry: Shapely Polygon or MultiPolygon
            
        Returns:
            SVG path data string
        """
        from shapely.geometry import Polygon, MultiPolygon
        
        def ring_to_path(ring) -> str:
            coords = list(ring.coords)
            if not coords:
                return ""
            
            # Start with move to first point
            path_parts = [f"M {coords[0][0]:.2f} {coords[0][1]:.2f}"]
            
            # Line to remaining points
            for x, y in coords[1:]:
                path_parts.append(f"L {x:.2f} {y:.2f}")
            
            # Close path
            path_parts.append("Z")
            
            return " ".join(path_parts)
        
        def polygon_to_path(poly: Polygon) -> str:
            parts = []
            
            # Exterior ring
            parts.append(ring_to_path(poly.exterior))
            
            # Interior rings (holes)
            for interior in poly.interiors:
                parts.append(ring_to_path(interior))
            
            return " ".join(parts)
        
        if isinstance(geometry, Polygon):
            return polygon_to_path(geometry)
        elif isinstance(geometry, MultiPolygon):
            paths = [polygon_to_path(poly) for poly in geometry.geoms]
            return " ".join(paths)
        else:
            logger.warning(f"Unsupported geometry type: {type(geometry)}")
            return ""
    
    def _format_hole_id(self, hole: int) -> str:
        """Format hole number as layer ID."""
        if hole == 98:
            return "Hole98_CartPaths"
        elif hole == 99:
            return "Hole99_OuterMesh"
        else:
            return f"Hole{hole:02d}"
    
    def generate(
        self,
        assignments_by_hole: Dict[int, List[HoleAssignment]],
    ) -> str:
        """
        Generate SVG content from hole assignments.
        
        Args:
            assignments_by_hole: Dictionary mapping holes to assignments
            
        Returns:
            SVG content as string
        """
        # Build CSS styles
        styles = []
        for feature_class, color in self.colors.items():
            styles.append(f"    .{feature_class} {{ fill: {color}; stroke: #000; stroke-width: {self.stroke_width}px; }}")
        
        style_block = "\n".join(styles)
        
        # Build layers
        layers = []
        
        # Process holes in order (1-18, then 98, 99)
        hole_order = list(range(1, 19)) + [98, 99]
        
        for hole in hole_order:
            if hole not in assignments_by_hole:
                continue
            
            assignments = assignments_by_hole[hole]
            layer_id = self._format_hole_id(hole)
            
            # Group paths by feature class for this hole
            paths = []
            for assignment in assignments:
                polygon = assignment.polygon
                path_data = self._polygon_to_path(polygon.geometry)
                
                if path_data:
                    paths.append(
                        f'      <path class="{polygon.feature_class}" '
                        f'd="{path_data}" '
                        f'data-id="{polygon.id}" '
                        f'data-confidence="{polygon.confidence:.3f}"/>'
                    )
            
            if paths:
                layer_content = "\n".join(paths)
                layers.append(
                    f'  <g id="{layer_id}" inkscape:groupmode="layer" inkscape:label="{layer_id}">\n'
                    f'{layer_content}\n'
                    f'  </g>'
                )
        
        layers_content = "\n".join(layers)
        
        # Assemble SVG
        svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
     width="{self.width}"
     height="{self.height}"
     viewBox="0 0 {self.width} {self.height}">
  <defs>
    <style type="text/css">
{style_block}
    </style>
  </defs>
{layers_content}
</svg>'''
        
        return svg
    
    def save(
        self,
        assignments_by_hole: Dict[int, List[HoleAssignment]],
        output_path: Path,
    ) -> None:
        """
        Generate and save SVG to file.
        
        Args:
            assignments_by_hole: Dictionary mapping holes to assignments
            output_path: Path to save SVG
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        svg_content = self.generate(assignments_by_hole)
        
        with open(output_path, "w") as f:
            f.write(svg_content)
        
        logger.info(f"Saved SVG to {output_path}")
    
    @staticmethod
    def load(svg_path: Path) -> str:
        """Load SVG content from file."""
        with open(svg_path) as f:
            return f.read()


class SVGCleaner:
    """
    Clean and optimize SVG geometry.
    
    Operations:
    - Union overlapping shapes of same class
    - Fix self-intersections
    - Simplify nodes
    - Optional fringe generation
    """
    
    def __init__(
        self,
        simplify_tolerance: float = 1.0,
        union_same_class: bool = True,
    ):
        """
        Initialize the SVG cleaner.
        
        Args:
            simplify_tolerance: Tolerance for node simplification
            union_same_class: Whether to union overlapping shapes of same class
        """
        self.simplify_tolerance = simplify_tolerance
        self.union_same_class = union_same_class
    
    def clean(
        self,
        assignments_by_hole: Dict[int, List[HoleAssignment]],
    ) -> Dict[int, List[HoleAssignment]]:
        """
        Clean and optimize geometry.
        
        Args:
            assignments_by_hole: Dictionary mapping holes to assignments
            
        Returns:
            Cleaned assignments dictionary
        """
        from shapely.ops import unary_union
        from shapely.validation import make_valid
        
        cleaned = {}
        
        for hole, assignments in assignments_by_hole.items():
            if self.union_same_class:
                # Group by feature class
                by_class: Dict[str, List[HoleAssignment]] = {}
                for assignment in assignments:
                    cls = assignment.polygon.feature_class
                    if cls not in by_class:
                        by_class[cls] = []
                    by_class[cls].append(assignment)
                
                # Union each class
                cleaned_assignments = []
                for feature_class, class_assignments in by_class.items():
                    geometries = [a.polygon.geometry for a in class_assignments]
                    
                    # Union and simplify
                    unioned = unary_union(geometries)
                    
                    if not unioned.is_valid:
                        unioned = make_valid(unioned)
                    
                    if self.simplify_tolerance > 0:
                        unioned = unioned.simplify(
                            self.simplify_tolerance,
                            preserve_topology=True,
                        )
                    
                    # Create new assignment with unioned geometry
                    # Use first assignment as template
                    template = class_assignments[0]
                    from .polygons import PolygonFeature
                    
                    new_polygon = PolygonFeature(
                        id=f"{feature_class}_{hole:02d}_merged",
                        feature_class=feature_class,
                        confidence=min(a.polygon.confidence for a in class_assignments),
                        geometry=unioned,
                        properties={"merged_count": len(class_assignments)},
                    )
                    
                    cleaned_assignments.append(HoleAssignment(
                        polygon=new_polygon,
                        hole=hole,
                    ))
                
                cleaned[hole] = cleaned_assignments
            else:
                # Just fix and simplify individual geometries
                cleaned_assignments = []
                for assignment in assignments:
                    geom = assignment.polygon.geometry
                    
                    if not geom.is_valid:
                        geom = make_valid(geom)
                    
                    if self.simplify_tolerance > 0:
                        geom = geom.simplify(
                            self.simplify_tolerance,
                            preserve_topology=True,
                        )
                    
                    # Create new polygon with cleaned geometry
                    from .polygons import PolygonFeature
                    
                    new_polygon = PolygonFeature(
                        id=assignment.polygon.id,
                        feature_class=assignment.polygon.feature_class,
                        confidence=assignment.polygon.confidence,
                        geometry=geom,
                        properties=assignment.polygon.properties,
                    )
                    
                    cleaned_assignments.append(HoleAssignment(
                        polygon=new_polygon,
                        hole=hole,
                    ))
                
                cleaned[hole] = cleaned_assignments
        
        logger.info(f"Cleaned SVG geometry for {len(cleaned)} holes")
        return cleaned
