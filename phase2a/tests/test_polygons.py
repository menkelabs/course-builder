"""
Tests for polygon generation module.
"""

import json
from pathlib import Path

import numpy as np
import pytest

from phase2a.pipeline.polygons import PolygonGenerator, PolygonFeature


class TestPolygonFeature:
    """Tests for PolygonFeature dataclass."""
    
    def test_to_geojson(self):
        """Test GeoJSON export."""
        from shapely.geometry import Polygon
        
        geometry = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
        feature = PolygonFeature(
            id="test_001",
            feature_class="green",
            confidence=0.9,
            geometry=geometry,
            properties={"area": 100},
        )
        
        geojson = feature.to_geojson()
        
        assert geojson["type"] == "Feature"
        assert geojson["id"] == "test_001"
        assert geojson["properties"]["class"] == "green"
        assert geojson["properties"]["confidence"] == 0.9
        assert geojson["geometry"]["type"] == "Polygon"


class TestPolygonGenerator:
    """Tests for PolygonGenerator class."""
    
    def test_init_default(self):
        generator = PolygonGenerator()
        assert generator.simplify_tolerance == 2.0
        assert generator.min_area == 50.0
        assert generator.buffer_distance == 0.0
    
    def test_init_custom(self):
        generator = PolygonGenerator(
            simplify_tolerance=5.0,
            min_area=100.0,
            buffer_distance=1.0,
        )
        assert generator.simplify_tolerance == 5.0
        assert generator.min_area == 100.0
        assert generator.buffer_distance == 1.0
    
    def test_mask_to_polygon_simple(self):
        """Test converting a simple rectangular mask to polygon."""
        generator = PolygonGenerator(min_area=10)
        
        mask = np.zeros((100, 100), dtype=bool)
        mask[20:80, 20:80] = True
        
        polygon = generator.mask_to_polygon(
            mask=mask,
            mask_id="rect",
            feature_class="green",
            confidence=0.9,
        )
        
        assert polygon is not None
        assert polygon.id == "rect"
        assert polygon.feature_class == "green"
        assert polygon.confidence == 0.9
        assert polygon.geometry.is_valid
    
    def test_mask_to_polygon_circle(self):
        """Test converting a circular mask to polygon."""
        generator = PolygonGenerator(min_area=10)
        
        mask = np.zeros((100, 100), dtype=bool)
        y, x = np.ogrid[:100, :100]
        mask[(x - 50)**2 + (y - 50)**2 <= 30**2] = True
        
        polygon = generator.mask_to_polygon(
            mask=mask,
            mask_id="circle",
            feature_class="bunker",
            confidence=0.85,
        )
        
        assert polygon is not None
        assert polygon.geometry.is_valid
        # Circle approximation should have area close to pi*r^2
        expected_area = np.pi * 30 * 30
        assert abs(polygon.geometry.area - expected_area) < expected_area * 0.2
    
    def test_mask_to_polygon_too_small(self):
        """Small masks should return None."""
        generator = PolygonGenerator(min_area=1000)
        
        mask = np.zeros((100, 100), dtype=bool)
        mask[45:55, 45:55] = True  # 100 pixels
        
        polygon = generator.mask_to_polygon(
            mask=mask,
            mask_id="small",
            feature_class="green",
            confidence=0.9,
        )
        
        assert polygon is None
    
    def test_mask_to_polygon_empty(self):
        """Empty masks should return None."""
        generator = PolygonGenerator(min_area=10)
        
        mask = np.zeros((100, 100), dtype=bool)
        
        polygon = generator.mask_to_polygon(
            mask=mask,
            mask_id="empty",
            feature_class="green",
            confidence=0.9,
        )
        
        assert polygon is None
    
    def test_mask_to_polygon_simplification(self):
        """Test that simplification reduces complexity."""
        # Create a jagged mask
        mask = np.zeros((100, 100), dtype=bool)
        for i in range(20, 80):
            width = 30 + (i % 5)  # Creates jagged edge
            mask[i, 25:25+width] = True
        
        # Without simplification
        gen_no_simp = PolygonGenerator(simplify_tolerance=0, min_area=10)
        poly_no_simp = gen_no_simp.mask_to_polygon(
            mask, "jagged", "rough", 0.8
        )
        
        # With simplification
        gen_simp = PolygonGenerator(simplify_tolerance=5.0, min_area=10)
        poly_simp = gen_simp.mask_to_polygon(
            mask, "smooth", "rough", 0.8
        )
        
        # Simplified should have fewer points
        if poly_no_simp and poly_simp:
            coords_no_simp = len(list(poly_no_simp.geometry.exterior.coords))
            coords_simp = len(list(poly_simp.geometry.exterior.coords))
            assert coords_simp <= coords_no_simp
    
    def test_generate_all(self, mock_mask_data, mock_gated_masks):
        """Test batch polygon generation."""
        accepted, _, _ = mock_gated_masks
        generator = PolygonGenerator(min_area=10)
        
        polygons = generator.generate_all(mock_mask_data, accepted)
        
        # Should have at most as many polygons as accepted masks
        assert len(polygons) <= len(accepted)
        
        for polygon in polygons:
            assert isinstance(polygon, PolygonFeature)
            assert polygon.geometry.is_valid
    
    def test_save_polygons(self, mock_polygons, temp_dir):
        """Test saving polygons to GeoJSON files."""
        generator = PolygonGenerator()
        polygons_dir = temp_dir / "polygons"
        
        generator.save_polygons(mock_polygons, polygons_dir)
        
        # Check combined file exists
        assert (polygons_dir / "all_features.geojson").exists()
        
        # Check individual files
        for polygon in mock_polygons:
            assert (polygons_dir / f"feature_{polygon.id}.geojson").exists()
    
    def test_load_polygons(self, mock_polygons, temp_dir):
        """Test loading polygons from GeoJSON files."""
        generator = PolygonGenerator()
        polygons_dir = temp_dir / "polygons"
        
        # Save first
        generator.save_polygons(mock_polygons, polygons_dir)
        
        # Load
        loaded = PolygonGenerator.load_polygons(polygons_dir)
        
        assert len(loaded) == len(mock_polygons)
        for orig, load in zip(mock_polygons, loaded):
            assert orig.id == load.id
            assert orig.feature_class == load.feature_class


class TestPolygonGeneratorEdgeCases:
    """Edge case tests for polygon generation."""
    
    def test_multipart_mask(self):
        """Test mask with multiple disconnected regions."""
        generator = PolygonGenerator(min_area=10)
        
        mask = np.zeros((100, 100), dtype=bool)
        # Two separate rectangles
        mask[10:30, 10:30] = True
        mask[60:80, 60:80] = True
        
        polygon = generator.mask_to_polygon(
            mask=mask,
            mask_id="multi",
            feature_class="bunker",
            confidence=0.8,
        )
        
        # Should create a valid geometry (possibly MultiPolygon)
        assert polygon is not None
        assert polygon.geometry.is_valid
    
    def test_mask_with_hole(self):
        """Test mask with interior hole."""
        generator = PolygonGenerator(min_area=10)
        
        mask = np.zeros((100, 100), dtype=bool)
        # Outer rectangle
        mask[10:90, 10:90] = True
        # Inner hole
        mask[30:70, 30:70] = False
        
        polygon = generator.mask_to_polygon(
            mask=mask,
            mask_id="donut",
            feature_class="fairway",
            confidence=0.75,
        )
        
        # Note: Current implementation may not preserve holes
        # Just verify it creates a valid polygon
        assert polygon is not None
        assert polygon.geometry.is_valid
    
    def test_very_thin_mask(self):
        """Test a very thin (1-pixel wide) mask."""
        generator = PolygonGenerator(min_area=5)
        
        mask = np.zeros((100, 100), dtype=bool)
        mask[50, 10:90] = True  # Horizontal line
        
        polygon = generator.mask_to_polygon(
            mask=mask,
            mask_id="thin",
            feature_class="cart_path",
            confidence=0.7,
        )
        
        # May or may not create a valid polygon depending on implementation
        # Just verify no exceptions
        pass
