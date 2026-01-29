"""
Tests for hole assignment module.
"""

import json
from pathlib import Path

import pytest
from shapely.geometry import Polygon

from phase1a.pipeline.holes import HoleAssigner, HoleAssignment, GreenCenter
from phase1a.pipeline.polygons import PolygonFeature


def make_polygon(x, y, size=20):
    """Helper to create a polygon at given location."""
    return Polygon([
        (x, y),
        (x + size, y),
        (x + size, y + size),
        (x, y + size),
    ])


@pytest.fixture
def sample_polygons():
    """Create sample polygons at various locations."""
    polygons = [
        PolygonFeature(
            id="p1",
            feature_class="green",
            confidence=0.9,
            geometry=make_polygon(120, 120),  # Near hole 1 center (128, 128)
            properties={},
        ),
        PolygonFeature(
            id="p2",
            feature_class="bunker",
            confidence=0.85,
            geometry=make_polygon(190, 40),  # Near hole 2 center (200, 50)
            properties={},
        ),
        PolygonFeature(
            id="p3",
            feature_class="fairway",
            confidence=0.8,
            geometry=make_polygon(40, 190),  # Near hole 3 center (50, 200)
            properties={},
        ),
        PolygonFeature(
            id="p4",
            feature_class="cart_path",
            confidence=0.75,
            geometry=make_polygon(100, 100),
            properties={},
        ),
    ]
    return polygons


class TestGreenCenter:
    """Tests for GreenCenter dataclass."""
    
    def test_creation(self):
        gc = GreenCenter(hole=1, x=100.0, y=200.0)
        assert gc.hole == 1
        assert gc.x == 100.0
        assert gc.y == 200.0


class TestHoleAssignment:
    """Tests for HoleAssignment dataclass."""
    
    def test_to_dict(self):
        polygon = PolygonFeature(
            id="test",
            feature_class="green",
            confidence=0.9,
            geometry=make_polygon(0, 0),
            properties={},
        )
        assignment = HoleAssignment(
            polygon=polygon,
            hole=5,
            distance_to_green=15.5,
        )
        
        data = assignment.to_dict()
        
        assert data["polygon_id"] == "test"
        assert data["feature_class"] == "green"
        assert data["hole"] == 5
        assert data["distance_to_green"] == 15.5


class TestHoleAssigner:
    """Tests for HoleAssigner class."""
    
    def test_init_default(self):
        assigner = HoleAssigner()
        assert assigner.green_centers == []
        assert assigner.max_distance == 1000.0
    
    def test_init_with_green_centers(self, sample_green_centers):
        assigner = HoleAssigner(green_centers=sample_green_centers)
        assert len(assigner.green_centers) == 3
        assert assigner.green_centers[0].hole == 1
    
    def test_assign_to_nearest_green(self, sample_green_centers, sample_polygons):
        assigner = HoleAssigner(green_centers=sample_green_centers)
        
        # Polygon near hole 1
        assignment = assigner.assign(sample_polygons[0])
        assert assignment.hole == 1
        assert assignment.distance_to_green is not None
    
    def test_assign_cart_path_to_hole_98(self, sample_green_centers, sample_polygons):
        assigner = HoleAssigner(green_centers=sample_green_centers)
        
        # Cart path polygon
        assignment = assigner.assign(sample_polygons[3])
        assert assignment.hole == 98
    
    def test_assign_without_green_centers(self, sample_polygons):
        assigner = HoleAssigner()
        
        # Should assign to outer mesh (99)
        assignment = assigner.assign(sample_polygons[0])
        assert assignment.hole == 99
    
    def test_assign_all(self, sample_green_centers, sample_polygons):
        assigner = HoleAssigner(green_centers=sample_green_centers)
        
        assignments_by_hole = assigner.assign_all(sample_polygons)
        
        # Should have assignments
        assert len(assignments_by_hole) > 0
        
        # Each assignment should be in correct structure
        for hole, assignments in assignments_by_hole.items():
            assert isinstance(hole, int)
            for a in assignments:
                assert isinstance(a, HoleAssignment)
                assert a.hole == hole
    
    def test_assign_all_groups_correctly(self, sample_green_centers, sample_polygons):
        assigner = HoleAssigner(green_centers=sample_green_centers)
        
        assignments_by_hole = assigner.assign_all(sample_polygons)
        
        # Cart path should be in hole 98
        if 98 in assignments_by_hole:
            cart_paths = [a for a in assignments_by_hole[98] 
                         if a.polygon.feature_class == "cart_path"]
            assert len(cart_paths) > 0
    
    def test_save_assignments(self, sample_green_centers, sample_polygons, temp_dir):
        assigner = HoleAssigner(green_centers=sample_green_centers)
        assignments_by_hole = assigner.assign_all(sample_polygons)
        
        output_path = temp_dir / "assignments.json"
        assigner.save_assignments(assignments_by_hole, output_path)
        
        assert output_path.exists()
        
        with open(output_path) as f:
            data = json.load(f)
        
        assert len(data) > 0
    
    def test_load_green_centers(self, green_centers_file):
        centers = HoleAssigner.load_green_centers(green_centers_file)
        
        assert len(centers) == 3
        assert centers[0]["hole"] == 1
        assert "x" in centers[0]
        assert "y" in centers[0]


class TestHoleAssignerEdgeCases:
    """Edge case tests for hole assignment."""
    
    def test_polygon_far_from_all_greens(self, sample_green_centers):
        """Polygon very far from all greens should go to outer mesh."""
        assigner = HoleAssigner(
            green_centers=sample_green_centers,
            max_distance=50,  # Very short max distance
        )
        
        # Polygon very far from any green center
        polygon = PolygonFeature(
            id="far",
            feature_class="rough",
            confidence=0.7,
            geometry=make_polygon(500, 500),
            properties={},
        )
        
        assignment = assigner.assign(polygon)
        assert assignment.hole == 99  # Outer mesh
    
    def test_polygon_equidistant_from_greens(self, sample_green_centers):
        """Polygon equidistant from two greens should pick one consistently."""
        # Green centers at (128, 128) and (200, 50)
        # Midpoint would be around (164, 89)
        assigner = HoleAssigner(green_centers=sample_green_centers)
        
        polygon = PolygonFeature(
            id="mid",
            feature_class="fairway",
            confidence=0.8,
            geometry=make_polygon(154, 79),  # Near midpoint
            properties={},
        )
        
        assignment = assigner.assign(polygon)
        
        # Should pick a valid hole (not outer mesh)
        assert assignment.hole in [1, 2, 3]
    
    def test_empty_polygon_list(self, sample_green_centers):
        assigner = HoleAssigner(green_centers=sample_green_centers)
        
        assignments_by_hole = assigner.assign_all([])
        
        assert len(assignments_by_hole) == 0
    
    def test_special_hole_numbers(self):
        """Verify special hole constants."""
        assert HoleAssigner.CART_PATH_HOLE == 98
        assert HoleAssigner.OUTER_MESH_HOLE == 99
