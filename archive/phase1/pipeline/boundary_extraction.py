"""
Boundary Extraction

Extract geographic bounds from user-selected boundaries in QGIS.
Supports multiple input formats: shapefiles, QGIS projects, GeoJSON.
"""

import logging
from pathlib import Path
from typing import Dict, Optional, Tuple
import json

logger = logging.getLogger(__name__)


def extract_bounds_from_shapefile(shapefile_path: Path) -> Dict[str, float]:
    """
    Extract geographic bounds from a shapefile.
    
    Args:
        shapefile_path: Path to shapefile (.shp file)
    
    Returns:
        Dictionary with bounds:
        {
            "northLat": float,
            "southLat": float,
            "eastLon": float,
            "westLon": float,
            "crs": str,
            "area_km2": float
        }
    """
    try:
        import geopandas as gpd
        from shapely.geometry import box
    except ImportError:
        logger.error("geopandas and shapely are required for boundary extraction")
        logger.error("Install with: pip install geopandas shapely")
        raise
    
    if not shapefile_path.exists():
        raise FileNotFoundError(f"Shapefile not found: {shapefile_path}")
    
    logger.info(f"Reading boundary from shapefile: {shapefile_path}")
    
    # Read shapefile
    gdf = gpd.read_file(shapefile_path)
    
    if gdf.empty:
        raise ValueError("Shapefile is empty - no features found")
    
    # Get bounding box [minx, miny, maxx, maxy]
    bounds = gdf.total_bounds
    
    # Calculate area (convert to km² if in meters)
    area_m2 = gdf.geometry.area.sum()
    crs = gdf.crs
    
    # Convert area to km²
    # If CRS is in meters (like UTM), convert directly
    # If CRS is in degrees (like WGS84), need to project to calculate area
    if crs and crs.is_geographic:
        # Project to a metric CRS for area calculation
        metric_crs = gdf.estimate_utm_crs()
        gdf_projected = gdf.to_crs(metric_crs)
        area_km2 = gdf_projected.geometry.area.sum() / 1e6
    else:
        area_km2 = area_m2 / 1e6
    
    result = {
        "westLon": float(bounds[0]),
        "southLat": float(bounds[1]),
        "eastLon": float(bounds[2]),
        "northLat": float(bounds[3]),
        "crs": str(crs) if crs else "EPSG:4326",
        "area_km2": float(area_km2)
    }
    
    logger.info(f"Extracted bounds: N:{result['northLat']:.6f}, "
                f"S:{result['southLat']:.6f}, "
                f"E:{result['eastLon']:.6f}, "
                f"W:{result['westLon']:.6f}")
    logger.info(f"Area: {result['area_km2']:.2f} km²")
    
    return result


def extract_bounds_from_geojson(geojson_path: Path) -> Dict[str, float]:
    """
    Extract geographic bounds from a GeoJSON file.
    
    Args:
        geojson_path: Path to GeoJSON file
    
    Returns:
        Dictionary with bounds (same format as extract_bounds_from_shapefile)
    """
    try:
        import geopandas as gpd
    except ImportError:
        logger.error("geopandas is required for GeoJSON extraction")
        raise
    
    if not geojson_path.exists():
        raise FileNotFoundError(f"GeoJSON file not found: {geojson_path}")
    
    logger.info(f"Reading boundary from GeoJSON: {geojson_path}")
    
    gdf = gpd.read_file(geojson_path)
    
    if gdf.empty:
        raise ValueError("GeoJSON is empty - no features found")
    
    # Use same extraction logic as shapefile
    return extract_bounds_from_shapefile(geojson_path)


def extract_bounds_from_qgis_project(
    project_path: Path,
    layer_name: str = "Course Boundary"
) -> Dict[str, float]:
    """
    Extract bounds from a specific layer in a QGIS project.
    
    This requires QGIS Python bindings and reads directly from the project.
    
    Args:
        project_path: Path to .qgz QGIS project file
        layer_name: Name of the layer containing the boundary
    
    Returns:
        Dictionary with bounds
    """
    from .qgis_env import setup_qgis_environment
    setup_qgis_environment()
    
    try:
        from qgis.core import (
            QgsProject,
            QgsApplication,
            QgsCoordinateReferenceSystem,
            QgsCoordinateTransform
        )
    except ImportError as e:
        logger.error(f"Failed to import QGIS modules: {e}")
        raise
    
    # Initialize QGIS
    QgsApplication.setPrefixPath('/usr', True)
    qgs = QgsApplication([], False)
    qgs.initQgis()
    
    try:
        project = QgsProject.instance()
        if not project.read(str(project_path)):
            raise Exception(f"Failed to read QGIS project: {project_path}")
        
        # Find the boundary layer
        layer = None
        for layer_id, layer_obj in project.mapLayers().items():
            if layer_obj.name() == layer_name:
                layer = layer_obj
                break
        
        if not layer:
            raise ValueError(f"Layer '{layer_name}' not found in project")
        
        if layer.featureCount() == 0:
            raise ValueError(f"Layer '{layer_name}' has no features")
        
        # Get extent
        extent = layer.extent()
        crs = layer.crs()
        
        # Transform to WGS84 if needed
        target_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        if crs != target_crs:
            transform = QgsCoordinateTransform(crs, target_crs, project)
            extent = transform.transform(extent)
        
        # Calculate area
        area = extent.width() * extent.height()
        # Rough conversion (not accurate for geographic CRS, but gives estimate)
        if crs.isGeographic():
            # Convert degrees to approximate km²
            # 1 degree lat ≈ 111 km, 1 degree lon varies by latitude
            lat_mid = (extent.yMinimum() + extent.yMaximum()) / 2
            lat_km = 111.0
            lon_km = 111.0 * abs(lat_mid / 90.0)  # Approximation
            area_km2 = (extent.width() * lon_km) * (extent.height() * lat_km)
        else:
            area_km2 = area / 1e6
        
        result = {
            "westLon": float(extent.xMinimum()),
            "southLat": float(extent.yMinimum()),
            "eastLon": float(extent.xMaximum()),
            "northLat": float(extent.yMaximum()),
            "crs": "EPSG:4326",
            "area_km2": float(area_km2)
        }
        
        logger.info(f"Extracted bounds from QGIS project layer")
        return result
    
    finally:
        qgs.exitQgis()


def validate_bounds(bounds: Dict[str, float]) -> Tuple[bool, Optional[str]]:
    """
    Validate that bounds are reasonable.
    
    Args:
        bounds: Dictionary with northLat, southLat, eastLon, westLon
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    required_keys = ["northLat", "southLat", "eastLon", "westLon"]
    for key in required_keys:
        if key not in bounds:
            return False, f"Missing required key: {key}"
    
    north = bounds["northLat"]
    south = bounds["southLat"]
    east = bounds["eastLon"]
    west = bounds["westLon"]
    
    # Check valid ranges
    if not (-90 <= south <= 90) or not (-90 <= north <= 90):
        return False, "Latitude must be between -90 and 90"
    
    if not (-180 <= west <= 180) or not (-180 <= east <= 180):
        return False, "Longitude must be between -180 and 180"
    
    # Check logical order
    if south >= north:
        return False, "South latitude must be less than north latitude"
    
    if west >= east:
        return False, "West longitude must be less than east longitude"
    
    # Check reasonable size (not too small, not too large)
    lat_span = north - south
    lon_span = east - west
    
    if lat_span < 0.001:  # Less than ~100m
        return False, "Boundary is too small (less than 100m)"
    
    if lat_span > 10 or lon_span > 10:  # More than ~1000km
        return False, "Boundary is too large (more than 1000km)"
    
    return True, None


def save_bounds_to_json(bounds: Dict[str, float], output_path: Path) -> Path:
    """
    Save bounds to a JSON file for use by Java backend or other tools.
    
    Args:
        bounds: Bounds dictionary
        output_path: Path to save JSON file
    
    Returns:
        Path to saved file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(bounds, f, indent=2)
    
    logger.info(f"Bounds saved to: {output_path}")
    return output_path
