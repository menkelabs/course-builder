"""
Tests for SVG generation module.

Tests verify the Inkscape-compatible SVG format matching RockRidge_No_Overlay.svg reference:
- Inline styles with opacity and fill
- inkscape:label on paths for feature identification
- Layer groups with inkscape:groupmode="layer"
"""

import re
from pathlib import Path

import pytest
from shapely.geometry import Polygon

from phase2a.pipeline.svg import SVGGenerator, SVGCleaner
from phase2a.pipeline.holes import HoleAssignment
from phase2a.pipeline.polygons import PolygonFeature


def make_polygon_feature(id, feature_class, coords):
    """Helper to create a PolygonFeature."""
    return PolygonFeature(
        id=id,
        feature_class=feature_class,
        confidence=0.9,
        geometry=Polygon(coords),
        properties={},
    )


@pytest.fixture
def sample_assignments():
    """Create sample hole assignments for testing."""
    assignments = {
        1: [
            HoleAssignment(
                polygon=make_polygon_feature(
                    "green_1", "green",
                    [(100, 100), (150, 100), (150, 150), (100, 150)]
                ),
                hole=1,
            ),
            HoleAssignment(
                polygon=make_polygon_feature(
                    "bunker_1", "bunker",
                    [(160, 120), (190, 120), (190, 140), (160, 140)]
                ),
                hole=1,
            ),
        ],
        2: [
            HoleAssignment(
                polygon=make_polygon_feature(
                    "fairway_2", "fairway",
                    [(200, 50), (300, 50), (300, 100), (200, 100)]
                ),
                hole=2,
            ),
        ],
        98: [
            HoleAssignment(
                polygon=make_polygon_feature(
                    "cart_1", "cart_path",
                    [(0, 0), (500, 0), (500, 10), (0, 10)]
                ),
                hole=98,
            ),
        ],
    }
    return assignments


class TestSVGGenerator:
    """Tests for SVGGenerator class."""
    
    def test_init_default(self):
        generator = SVGGenerator()
        assert generator.width == 4096
        assert generator.height == 4096
        assert generator.opacity == 0.5
        assert "water" in generator.colors
    
    def test_init_custom(self):
        generator = SVGGenerator(
            width=1024,
            height=768,
            colors={"water": "#0000ff"},
            opacity=0.7,
        )
        assert generator.width == 1024
        assert generator.height == 768
        assert generator.colors["water"] == "#0000ff"
        assert generator.opacity == 0.7
    
    def test_format_hole_label(self):
        generator = SVGGenerator()
        
        # New format: Hole1, Hole9, Hole18 (no zero padding)
        assert generator._format_hole_label(1) == "Hole1"
        assert generator._format_hole_label(9) == "Hole9"
        assert generator._format_hole_label(18) == "Hole18"
        assert generator._format_hole_label(98) == "Hole98"
        assert generator._format_hole_label(99) == "Hole99"
    
    def test_polygon_to_path_simple(self):
        generator = SVGGenerator()
        polygon = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
        
        path = generator._polygon_to_path(polygon)
        
        # Should start with m (relative moveto) and end with z (close)
        assert path.startswith("m")
        assert path.endswith("z")
        # Should have relative coordinates (commas separate x,y)
        assert "," in path
    
    def test_generate_basic(self, sample_assignments):
        generator = SVGGenerator(width=512, height=512)
        
        svg = generator.generate(sample_assignments)
        
        # Should be valid XML
        assert svg.startswith("<?xml")
        assert "</svg>" in svg
        
        # Should have layers with Inkscape format (no zero padding)
        assert 'inkscape:label="Hole1"' in svg
        assert 'inkscape:label="Hole2"' in svg
        assert 'inkscape:label="Hole98"' in svg
    
    def test_generate_has_inline_styles(self, sample_assignments):
        generator = SVGGenerator()
        
        svg = generator.generate(sample_assignments)
        
        # Should have inline styles with opacity and fill (not CSS classes)
        assert 'style="opacity:0.5;fill:#' in svg
        # Should NOT have CSS style block
        assert ".green {" not in svg
        assert ".bunker {" not in svg
    
    def test_generate_has_viewbox(self, sample_assignments):
        generator = SVGGenerator(width=1024, height=768)
        
        svg = generator.generate(sample_assignments)
        
        assert 'viewBox="0 0 1024 768"' in svg
    
    def test_generate_paths_have_inkscape_label(self, sample_assignments):
        generator = SVGGenerator()
        
        svg = generator.generate(sample_assignments)
        
        # Paths should have inkscape:label attribute for feature identification
        assert 'inkscape:label="green1"' in svg
        assert 'inkscape:label="bunker"' in svg
        assert 'inkscape:label="fairway2"' in svg
    
    def test_generate_paths_have_id(self, sample_assignments):
        generator = SVGGenerator()
        
        svg = generator.generate(sample_assignments)
        
        # Should have path IDs
        assert 'id="path1"' in svg
        assert 'id="path2"' in svg
    
    def test_save(self, sample_assignments, temp_dir):
        generator = SVGGenerator()
        output_path = temp_dir / "course.svg"
        
        generator.save(sample_assignments, output_path)
        
        assert output_path.exists()
        
        with open(output_path) as f:
            content = f.read()
        
        assert content.startswith("<?xml")
        # Document name should match filename
        assert 'sodipodi:docname="course.svg"' in content
    
    def test_load(self, sample_assignments, temp_dir):
        generator = SVGGenerator()
        output_path = temp_dir / "course.svg"
        
        generator.save(sample_assignments, output_path)
        content = SVGGenerator.load(output_path)
        
        assert 'inkscape:label="Hole1"' in content


class TestSVGGeneratorColors:
    """Tests for SVG color handling."""
    
    def test_default_colors(self):
        generator = SVGGenerator()
        
        # Colors should be from OPCD v4 palette (lowercase hex)
        assert generator.colors["water"] == "#0000c0"  # Lake from OPCD
        assert generator.colors["bunker"] == "#e5e5aa"  # Bunker from OPCD
        assert generator.colors["green"] == "#bce5a4"  # Green from OPCD
        assert generator.colors["fairway"] == "#43e561"  # Fairway from OPCD
        assert generator.colors["rough"] == "#278438"  # Rough from OPCD
    
    def test_custom_colors_override(self):
        generator = SVGGenerator(colors={"water": "#0000ff"})
        
        # Custom color should override OPCD palette
        assert generator.colors["water"] == "#0000ff"
        # Others should remain OPCD defaults (lowercase)
        assert generator.colors["green"] == "#bce5a4"  # OPCD Green
    
    def test_colors_in_generated_svg(self, sample_assignments):
        generator = SVGGenerator(colors={"green": "#00ff00"})
        
        svg = generator.generate(sample_assignments)
        
        # Custom color should appear in inline styles
        assert "fill:#00ff00" in svg


class TestSVGCleaner:
    """Tests for SVGCleaner class."""
    
    def test_init_default(self):
        cleaner = SVGCleaner()
        assert cleaner.simplify_tolerance == 1.0
        assert cleaner.union_same_class is True
    
    def test_clean_simplifies_geometry(self, sample_assignments):
        cleaner = SVGCleaner(simplify_tolerance=5.0)
        
        cleaned = cleaner.clean(sample_assignments)
        
        # Should return valid assignments
        assert len(cleaned) > 0
        for hole, assignments in cleaned.items():
            for a in assignments:
                assert a.polygon.geometry.is_valid
    
    def test_clean_unions_same_class(self):
        """Test that overlapping shapes of same class are unioned."""
        # Create two overlapping green polygons
        assignments = {
            1: [
                HoleAssignment(
                    polygon=make_polygon_feature(
                        "green_a", "green",
                        [(0, 0), (20, 0), (20, 20), (0, 20)]
                    ),
                    hole=1,
                ),
                HoleAssignment(
                    polygon=make_polygon_feature(
                        "green_b", "green",
                        [(10, 10), (30, 10), (30, 30), (10, 30)]
                    ),
                    hole=1,
                ),
            ],
        }
        
        cleaner = SVGCleaner(union_same_class=True)
        cleaned = cleaner.clean(assignments)
        
        # Should have merged into one
        assert len(cleaned[1]) == 1
        assert cleaned[1][0].polygon.feature_class == "green"
    
    def test_clean_preserves_different_classes(self):
        """Test that different classes are not unioned."""
        assignments = {
            1: [
                HoleAssignment(
                    polygon=make_polygon_feature(
                        "green_1", "green",
                        [(0, 0), (20, 0), (20, 20), (0, 20)]
                    ),
                    hole=1,
                ),
                HoleAssignment(
                    polygon=make_polygon_feature(
                        "bunker_1", "bunker",
                        [(10, 10), (30, 10), (30, 30), (10, 30)]
                    ),
                    hole=1,
                ),
            ],
        }
        
        cleaner = SVGCleaner(union_same_class=True)
        cleaned = cleaner.clean(assignments)
        
        # Should still have two separate features
        assert len(cleaned[1]) == 2
    
    def test_clean_without_union(self):
        """Test cleaning without unioning."""
        assignments = {
            1: [
                HoleAssignment(
                    polygon=make_polygon_feature(
                        "green_a", "green",
                        [(0, 0), (20, 0), (20, 20), (0, 20)]
                    ),
                    hole=1,
                ),
                HoleAssignment(
                    polygon=make_polygon_feature(
                        "green_b", "green",
                        [(10, 10), (30, 10), (30, 30), (10, 30)]
                    ),
                    hole=1,
                ),
            ],
        }
        
        cleaner = SVGCleaner(union_same_class=False)
        cleaned = cleaner.clean(assignments)
        
        # Should preserve both
        assert len(cleaned[1]) == 2


class TestSVGGeneratorEdgeCases:
    """Edge case tests for SVG generation."""
    
    def test_empty_assignments(self):
        generator = SVGGenerator()
        
        svg = generator.generate({})
        
        # Should still produce valid SVG
        assert svg.startswith("<?xml")
        assert "</svg>" in svg
    
    def test_hole_with_no_features(self):
        """Test hole in range but no features."""
        generator = SVGGenerator()
        
        # Only hole 5 has features
        assignments = {
            5: [
                HoleAssignment(
                    polygon=make_polygon_feature(
                        "green_5", "green",
                        [(0, 0), (10, 0), (10, 10), (0, 10)]
                    ),
                    hole=5,
                ),
            ],
        }
        
        svg = generator.generate(assignments)
        
        # Should have hole 5 (new format, no zero padding)
        assert 'inkscape:label="Hole5"' in svg
        # Should NOT have holes 1-4
        assert 'inkscape:label="Hole1"' not in svg
    
    def test_multipolygon_feature(self):
        """Test feature with MultiPolygon geometry."""
        from shapely.geometry import MultiPolygon
        
        generator = SVGGenerator()
        
        multi = MultiPolygon([
            Polygon([(0, 0), (10, 0), (10, 10), (0, 10)]),
            Polygon([(20, 20), (30, 20), (30, 30), (20, 30)]),
        ])
        
        feature = PolygonFeature(
            id="multi",
            feature_class="bunker",
            confidence=0.8,
            geometry=multi,
            properties={},
        )
        
        assignments = {
            1: [HoleAssignment(polygon=feature, hole=1)],
        }
        
        svg = generator.generate(assignments)
        
        # Should handle multipolygon
        assert "<path" in svg


class TestSVGGeneratorInkscapeCompatibility:
    """Tests for Inkscape-specific format compatibility."""
    
    def test_has_inkscape_namespaces(self, sample_assignments):
        generator = SVGGenerator()
        svg = generator.generate(sample_assignments)
        
        # Should have Inkscape and Sodipodi namespaces
        assert 'xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"' in svg
        assert 'xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"' in svg
    
    def test_layers_have_groupmode(self, sample_assignments):
        generator = SVGGenerator()
        svg = generator.generate(sample_assignments)
        
        # Layers should have inkscape:groupmode="layer"
        assert 'inkscape:groupmode="layer"' in svg
    
    def test_has_sodipodi_namedview(self, sample_assignments):
        generator = SVGGenerator()
        svg = generator.generate(sample_assignments)
        
        # Should have sodipodi:namedview for Inkscape settings
        assert '<sodipodi:namedview' in svg
    
    def test_has_defs_element(self, sample_assignments):
        generator = SVGGenerator()
        svg = generator.generate(sample_assignments)
        
        # Should have defs element (even if empty)
        assert '<defs' in svg
    
    def test_svg_version(self, sample_assignments):
        generator = SVGGenerator()
        svg = generator.generate(sample_assignments)
        
        # Should have version 1.1
        assert 'version="1.1"' in svg
