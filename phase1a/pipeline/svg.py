"""
SVG Generation Module

Generates structured SVG files with per-hole layers in Inkscape-compatible format.

Output format matches the RockRidge_No_Overlay.svg reference:
- Inline styles with opacity:0.5;fill:#XXXXXX
- inkscape:label on paths for feature type identification
- Layer groups with inkscape:groupmode="layer" and inkscape:label="HoleN"
- Sodipodi namespace for Inkscape compatibility
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Optional, Any
import logging

from .holes import HoleAssignment

logger = logging.getLogger(__name__)


class SVGGenerator:
    """
    Generate course SVG with structured layers in Inkscape-compatible format.
    
    Layers:
    - Hole1 through Hole18
    - Hole98 (CartPaths)
    - Hole99 (OuterMesh)
    
    Features are identified by inkscape:label attribute on paths:
    - rough, semi, fairway, green, tee, bunker, water, cart_path
    
    Colors (OPCD palette):
    - water: #0000C0 (Lake)
    - bunker: #E5E5AA
    - green: #BCE5A4
    - fairway: #43E561
    - semi: #36B74D (semi-rough)
    - rough: #278438
    - tee: #A0E5B8
    - cart_path: #BEBEBB (Concrete)
    - hole99: #FF00CB
    """
    
    @staticmethod
    def load_opcd_palette(palette_path: Optional[Path] = None) -> Dict[str, str]:
        """
        Load OPCD color palette from GPL file.
        
        Args:
            palette_path: Path to color_defaults.gpl file. If None, uses default location.
            
        Returns:
            Dictionary mapping feature names to hex colors
        """
        if palette_path is None:
            # Default to resources directory
            palette_path = Path(__file__).parent.parent / "resources" / "color_defaults.gpl"
        
        palette_path = Path(palette_path)
        if not palette_path.exists():
            logger.warning(f"OPCD palette not found at {palette_path}, using defaults")
            return SVGGenerator._get_default_colors()
        
        colors = {}
        with open(palette_path, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                
                # Parse GPL format: "R G B #HEX #Name"
                # Example: "188 229 164 #BCE5A4   #Green - Blend 0.12m"
                match = re.match(r'(\d+)\s+(\d+)\s+(\d+)\s+#([0-9A-Fa-f]{6})\s*#(.*)', line)
                if match:
                    r, g, b, hex_color, name = match.groups()
                    # Extract base name (before dash)
                    base_name = name.split('-')[0].strip().lower()
                    hex_color = f"#{hex_color.lower()}"
                    
                    # Map to feature classes
                    if 'green' in base_name:
                        colors['green'] = hex_color
                    elif 'fairway' in base_name:
                        colors['fairway'] = hex_color
                    elif 'semi' in base_name:
                        colors['semi'] = hex_color
                    elif 'rough' in base_name and 'deep' not in base_name:
                        colors['rough'] = hex_color
                    elif 'bunker' in base_name:
                        colors['bunker'] = hex_color
                    elif 'tee' in base_name:
                        colors['tee'] = hex_color
                    elif 'lake' in base_name:
                        colors['water'] = hex_color
                    elif 'creek' in base_name:
                        colors['creek'] = hex_color
                    elif 'concrete' in base_name:
                        colors['cart_path'] = hex_color
                    elif 'hole99' in base_name.lower():
                        colors['hole99'] = hex_color
        
        # Ensure all required colors are present
        default_colors = SVGGenerator._get_default_colors()
        for key, default_value in default_colors.items():
            if key not in colors:
                colors[key] = default_value
                logger.warning(f"Missing color for {key}, using default {default_value}")
        
        logger.info(f"Loaded OPCD palette from {palette_path}")
        return colors
    
    @staticmethod
    def _get_default_colors() -> Dict[str, str]:
        """Get default OPCD colors (fallback if palette file not found)."""
        return {
            "water": "#0000c0",      # Lake
            "bunker": "#e5e5aa",     # Bunker
            "green": "#bce5a4",      # Green
            "fairway": "#43e561",    # Fairway
            "semi": "#36b74d",       # Semi-rough
            "rough": "#278438",      # Rough
            "tee": "#a0e5b8",        # Tee
            "cart_path": "#bebebb",  # Concrete
            "ignore": "#cccccc",     # Neutral gray
            "hole99": "#ff00cb",     # Hole99
        }
    
    # OPCD color palette - loaded from GPL file
    DEFAULT_COLORS = _get_default_colors()
    
    def __init__(
        self,
        width: int = 4096,
        height: int = 4096,
        colors: Optional[Dict[str, str]] = None,
        opacity: float = 0.5,
        palette_path: Optional[Path] = None,
    ):
        """
        Initialize the SVG generator.
        
        Args:
            width: SVG width in pixels (also used for viewBox)
            height: SVG height in pixels (also used for viewBox)
            colors: Custom color palette (overrides defaults)
            opacity: Opacity for path fills (default 0.5, matching reference SVG)
            palette_path: Path to color_defaults.gpl palette file (auto-detected if None)
        """
        self.width = width
        self.height = height
        self.opacity = opacity
        
        # Load OPCD palette from GPL file
        opcd_colors = self.load_opcd_palette(palette_path)
        
        # Merge: OPCD palette -> custom colors -> defaults
        self.colors = {**opcd_colors, **(colors or {})}
        
        # Counter for generating unique path IDs
        self._path_counter = 0
    
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
            path_parts = [f"m {coords[0][0]:.4f},{coords[0][1]:.4f}"]
            
            # Use relative coordinates (c for curves would be better, but l for lines works)
            prev_x, prev_y = coords[0]
            for x, y in coords[1:]:
                dx = x - prev_x
                dy = y - prev_y
                path_parts.append(f"{dx:.4f},{dy:.4f}")
                prev_x, prev_y = x, y
            
            # Close path
            path_parts.append("z")
            
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
    
    def _format_layer_id(self, hole: int) -> str:
        """Format hole number as layer ID (e.g., 'layer1' for hole 1)."""
        if hole == 99:
            return "layer1"  # Hole99 is typically first layer
        elif hole == 98:
            return f"layer{hole}"
        else:
            # Holes 1-18 get sequential layer IDs after Hole99
            return f"layer{hole + 1}"
    
    def _format_hole_label(self, hole: int) -> str:
        """Format hole number as inkscape:label (e.g., 'Hole1', 'Hole99')."""
        return f"Hole{hole}"
    
    def _get_next_path_id(self) -> str:
        """Generate a unique path ID."""
        self._path_counter += 1
        return f"path{self._path_counter}"
    
    def _format_feature_label(self, feature_class: str, hole: int, index: int = 0) -> str:
        """
        Format feature label for inkscape:label attribute.
        
        Examples: 'rough', 'green1', 'fairway1-1', 'bunker', 'tee1'
        """
        # Map feature class to label format used in reference SVG
        label_map = {
            "green": f"green{hole}",
            "fairway": f"fairway{hole}" if index == 0 else f"fairway{hole}-{index}",
            "tee": f"tee{hole}" if index == 0 else f"tee{hole}-{index}",
            "rough": "rough",
            "semi": "semi" if index == 0 else f"semi-{hole}-{index}",
            "bunker": "bunker",
            "water": "water",
            "cart_path": "cart_path",
        }
        return label_map.get(feature_class, feature_class)
    
    def generate(
        self,
        assignments_by_hole: Dict[int, List[HoleAssignment]],
        document_name: str = "course.svg",
    ) -> str:
        """
        Generate SVG content from hole assignments in Inkscape-compatible format.
        
        Args:
            assignments_by_hole: Dictionary mapping holes to assignments
            document_name: Name for sodipodi:docname attribute
            
        Returns:
            SVG content as string
        """
        # Reset path counter
        self._path_counter = 0
        
        # Build layers
        layers = []
        
        # Process holes in order: 99 first (outer mesh), then 1-18, then 98 (cart paths)
        hole_order = [99] + list(range(1, 19)) + [98]
        
        for hole in hole_order:
            if hole not in assignments_by_hole:
                continue
            
            assignments = assignments_by_hole[hole]
            layer_id = self._format_layer_id(hole)
            layer_label = self._format_hole_label(hole)
            
            # Track feature counts for generating unique labels
            feature_counts: Dict[str, int] = {}
            
            # Build paths for this hole
            paths = []
            for assignment in assignments:
                polygon = assignment.polygon
                path_data = self._polygon_to_path(polygon.geometry)
                
                if not path_data:
                    continue
                
                # Get color for this feature
                feature_class = polygon.feature_class
                color = self.colors.get(feature_class, self.colors.get("ignore", "#cccccc"))
                
                # Generate feature label with index
                feature_index = feature_counts.get(feature_class, 0)
                feature_counts[feature_class] = feature_index + 1
                feature_label = self._format_feature_label(feature_class, hole, feature_index)
                
                # Generate unique path ID
                path_id = self._get_next_path_id()
                
                # Build path element with inline style (matching reference format)
                path_elem = (
                    f'    <path\n'
                    f'       style="opacity:{self.opacity};fill:{color}"\n'
                    f'       d="{path_data}"\n'
                    f'       id="{path_id}"\n'
                    f'       inkscape:label="{feature_label}" />'
                )
                paths.append(path_elem)
            
            if paths:
                paths_content = "\n".join(paths)
                # Determine layer style
                layer_style = "display:inline"
                if hole == 99:
                    layer_style = "display:inline;opacity:1"
                
                layer_elem = (
                    f'  <g\n'
                    f'     inkscape:groupmode="layer"\n'
                    f'     id="{layer_id}"\n'
                    f'     inkscape:label="{layer_label}"\n'
                    f'     style="{layer_style}">\n'
                    f'{paths_content}\n'
                    f'  </g>'
                )
                layers.append(layer_elem)
        
        layers_content = "\n".join(layers)
        
        # Assemble SVG with Inkscape-compatible format
        svg = f'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<!-- Generated by Phase 1A Golf Course Builder -->

<svg
   version="1.1"
   id="svg1"
   width="{self.width}"
   height="{self.height}"
   viewBox="0 0 {self.width} {self.height}"
   sodipodi:docname="{document_name}"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:svg="http://www.w3.org/2000/svg">
  <defs
     id="defs1" />
  <sodipodi:namedview
     id="namedview1"
     pagecolor="#ffffff"
     bordercolor="#000000"
     borderopacity="0.25"
     inkscape:showpageshadow="2"
     inkscape:pageopacity="0.0"
     inkscape:pagecheckerboard="0"
     inkscape:deskcolor="#d1d1d1" />
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
        
        # Use filename as document name
        document_name = output_path.name
        svg_content = self.generate(assignments_by_hole, document_name=document_name)
        
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
