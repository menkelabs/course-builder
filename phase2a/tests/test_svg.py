"""
Tests for SVG generation module.
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
        assert generator.stroke_width == 1.0
        assert "water" in generator.colors
    
    def test_init_custom(self):
        generator = SVGGenerator(
            width=1024,
            height=768,
            colors={"water": "#0000ff"},
            stroke_width=2.0,
        )
        assert generator.width == 1024
        assert generator.height == 768
        assert generator.colors["water"] == "#0000ff"
        assert generator.stroke_width == 2.0
    
    def test_format_hole_id(self):
        generator = SVGGenerator()
        
        assert generator._format_hole_id(1) == "Hole01"
        assert generator._format_hole_id(9) == "Hole09"
        assert generator._format_hole_id(18) == "Hole18"
        assert generator._format_hole_id(98) == "Hole98_CartPaths"
        assert generator._format_hole_id(99) == "Hole99_OuterMesh"
    
    def test_polygon_to_path_simple(self):
        generator = SVGGenerator()
        polygon = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
        
        path = generator._polygon_to_path(polygon)
        
        # Should start with M (moveto) and end with Z (close)
        assert path.startswith("M")
        assert path.endswith("Z")
        # Should have L commands
        assert "L" in path
    
    def test_generate_basic(self, sample_assignments):
        generator = SVGGenerator(width=512, height=512)
        
        svg = generator.generate(sample_assignments)
        
        # Should be valid XML
        assert svg.startswith("<?xml")
        assert "</svg>" in svg
        
        # Should have layers
        assert "Hole01" in svg
        assert "Hole02" in svg
        assert "Hole98_CartPaths" in svg
    
    def test_generate_has_styles(self, sample_assignments):
        generator = SVGGenerator()
        
        svg = generator.generate(sample_assignments)
        
        # Should have CSS classes
        assert ".green" in svg
        assert ".bunker" in svg
        assert ".fairway" in svg
    
    def test_generate_has_viewbox(self, sample_assignments):
        generator = SVGGenerator(width=1024, height=768)
        
        svg = generator.generate(sample_assignments)
        
        assert 'viewBox="0 0 1024 768"' in svg
    
    def test_generate_paths_have_class(self, sample_assignments):
        generator = SVGGenerator()
        
        svg = generator.generate(sample_assignments)
        
        # Paths should have class attribute
        assert 'class="green"' in svg
        assert 'class="bunker"' in svg
    
    def test_generate_paths_have_data_attributes(self, sample_assignments):
        generator = SVGGenerator()
        
        svg = generator.generate(sample_assignments)
        
        # Should have data attributes for identification
        assert 'data-id=' in svg
        assert 'data-confidence=' in svg
    
    def test_save(self, sample_assignments, temp_dir):
        generator = SVGGenerator()
        output_path = temp_dir / "course.svg"
        
        generator.save(sample_assignments, output_path)
        
        assert output_path.exists()
        
        with open(output_path) as f:
            content = f.read()
        
        assert content.startswith("<?xml")
    
    def test_load(self, sample_assignments, temp_dir):
        generator = SVGGenerator()
        output_path = temp_dir / "course.svg"
        
        generator.save(sample_assignments, output_path)
        content = SVGGenerator.load(output_path)
        
        assert "Hole01" in content


class TestSVGGeneratorColors:
    """Tests for SVG color handling."""
    
    def test_default_colors(self):
        generator = SVGGenerator()
        
        assert generator.colors["water"] == "#0066cc"
        assert generator.colors["bunker"] == "#f5deb3"
        assert generator.colors["green"] == "#228b22"
        assert generator.colors["fairway"] == "#90ee90"
        assert generator.colors["rough"] == "#556b2f"
    
    def test_custom_colors_override(self):
        generator = SVGGenerator(colors={"water": "#0000ff"})
        
        # Custom color should override
        assert generator.colors["water"] == "#0000ff"
        # Others should remain default
        assert generator.colors["green"] == "#228b22"
    
    def test_colors_in_generated_svg(self, sample_assignments):
        generator = SVGGenerator(colors={"green": "#00ff00"})
        
        svg = generator.generate(sample_assignments)
        
        # Custom color should appear in styles
        assert "#00ff00" in svg


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
        
        # Should have hole 5 but not holes 1-4
        assert "Hole05" in svg
        assert "Hole01" not in svg
    
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
