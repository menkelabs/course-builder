"""
Phase1 Actions for the Python Agent.

Exposes Phase1 (QGIS/GDAL terrain preparation) functionality as remote actions.

Actions:
- phase1_run: Run complete Phase1 pipeline
- phase1_geocode: Geocode a location to coordinates
- phase1_download_dem: Download DEM data for area
- phase1_generate_heightmap: Generate heightmap from DEM
"""

import logging
import sys
from pathlib import Path
from typing import Dict, Any

from ..registry import get_registry
from ..models import Io, DynamicType, PropertyDef

logger = logging.getLogger(__name__)

# Get the global registry
registry = get_registry()


# =============================================================================
# Type Definitions
# =============================================================================

Phase1Config = DynamicType(
    name="Phase1Config",
    description="Configuration for Phase1 pipeline execution",
    own_properties=[
        PropertyDef("course_name", "string", "Name of the golf course"),
        PropertyDef("location", "string", "Location to geocode (address or coords)"),
        PropertyDef("output_dir", "string", "Output directory for pipeline artifacts"),
        PropertyDef("dem_source", "string", "DEM data source (usgs, copernicus, etc)"),
        PropertyDef("resolution", "number", "Target resolution in meters"),
    ],
)

Phase1Result = DynamicType(
    name="Phase1Result",
    description="Result from Phase1 pipeline execution",
    own_properties=[
        PropertyDef("heightmap_path", "string", "Path to generated heightmap"),
        PropertyDef("satellite_path", "string", "Path to satellite image"),
        PropertyDef("bounds", "object", "Geographic bounds {north, south, east, west}"),
        PropertyDef("crs", "string", "Coordinate reference system"),
    ],
)

GeocodeResult = DynamicType(
    name="GeocodeResult",
    description="Result from geocoding",
    own_properties=[
        PropertyDef("latitude", "number", "Latitude in decimal degrees"),
        PropertyDef("longitude", "number", "Longitude in decimal degrees"),
        PropertyDef("display_name", "string", "Display name of location"),
    ],
)

# Register types
for dtype in [Phase1Config, Phase1Result, GeocodeResult]:
    registry.register_type(dtype)


# =============================================================================
# Action Handlers
# =============================================================================

@registry.action(
    name="phase1_run",
    description="Run the complete Phase1 pipeline: geocoding → DEM download → "
                "heightmap generation → satellite imagery acquisition.",
    inputs=[Io("config", "Phase1Config")],
    outputs=[Io("result", "Phase1Result")],
    pre=["course_name_defined"],
    post=["terrain_ready", "satellite_image_exists"],
    cost=0.9,
    value=0.8,
    can_rerun=True,
)
async def phase1_run(params: Dict[str, Any]) -> Dict[str, Any]:
    """Run complete Phase1 pipeline."""
    config = params.get("config", params)
    course_name = config.get("course_name", "unknown")
    location = config.get("location")
    output_dir = config.get("output_dir", f"/output/{course_name}/phase1/")
    
    # Try to use actual phase1 client
    try:
        phase1_path = Path(__file__).parent.parent.parent.parent / "phase1"
        if str(phase1_path) not in sys.path:
            sys.path.insert(0, str(phase1_path.parent))
        
        from phase1.client import Phase1Client
        from phase1.config import Phase1Config as Phase1ConfigClass
        
        # Use actual client
        cfg = Phase1ConfigClass()
        cfg.course_name = course_name
        cfg.output_dir = Path(output_dir)
        if location:
            cfg.location = location
        
        client = Phase1Client(cfg)
        result = client.run()
        
        return {
            "heightmap_path": str(result.heightmap_path),
            "satellite_path": str(result.satellite_path),
            "bounds": {
                "north": result.bounds.north,
                "south": result.bounds.south,
                "east": result.bounds.east,
                "west": result.bounds.west,
            },
            "crs": result.crs,
        }
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"Phase1 client error: {e}")
    
    # Return mock result
    return {
        "heightmap_path": f"{output_dir}/heightmap.tif",
        "satellite_path": f"{output_dir}/satellite.png",
        "bounds": {
            "north": 40.7,
            "south": 40.6,
            "east": -74.0,
            "west": -74.1,
        },
        "crs": "EPSG:4326",
        "_mock": True,
    }


@registry.action(
    name="phase1_geocode",
    description="Geocode a location string to geographic coordinates.",
    inputs=[Io("location", "string")],
    outputs=[Io("result", "GeocodeResult")],
    pre=[],
    post=["location_geocoded"],
    cost=0.1,
    value=0.2,
    can_rerun=True,
)
async def phase1_geocode(params: Dict[str, Any]) -> Dict[str, Any]:
    """Geocode a location to coordinates."""
    location = params.get("location")
    
    if not location:
        raise ValueError("Location is required")
    
    try:
        phase1_path = Path(__file__).parent.parent.parent.parent / "phase1"
        if str(phase1_path) not in sys.path:
            sys.path.insert(0, str(phase1_path.parent))
        
        from phase1.pipeline.geocoding import geocode
        
        result = geocode(location)
        
        return {
            "latitude": result["lat"],
            "longitude": result["lon"],
            "display_name": result.get("display_name", location),
        }
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"Geocoding error: {e}")
    
    # Mock result - use simple parsing for coords
    if "," in location:
        try:
            parts = location.split(",")
            lat, lon = float(parts[0].strip()), float(parts[1].strip())
            return {
                "latitude": lat,
                "longitude": lon,
                "display_name": location,
            }
        except ValueError:
            pass
    
    # Default mock
    return {
        "latitude": 40.6892,
        "longitude": -74.0445,
        "display_name": f"Geocoded: {location}",
        "_mock": True,
    }


@registry.action(
    name="phase1_download_dem",
    description="Download DEM (Digital Elevation Model) data for a geographic area.",
    inputs=[
        Io("bounds", "object"),
        Io("output_dir", "string"),
        Io("source", "string"),
    ],
    outputs=[Io("dem_path", "string")],
    pre=["location_geocoded"],
    post=["dem_downloaded"],
    cost=0.5,
    value=0.3,
    can_rerun=True,
)
async def phase1_download_dem(params: Dict[str, Any]) -> Dict[str, Any]:
    """Download DEM data for area."""
    bounds = params.get("bounds", {})
    output_dir = params.get("output_dir", "/output/dem/")
    source = params.get("source", "copernicus")
    
    # Mock result for now
    return {
        "dem_path": f"{output_dir}/dem.tif",
        "source": source,
        "bounds": bounds,
        "_mock": True,
    }


@registry.action(
    name="phase1_generate_heightmap",
    description="Generate heightmap from DEM data for Unity terrain.",
    inputs=[
        Io("dem_path", "string"),
        Io("output_path", "string"),
        Io("resolution", "number"),
    ],
    outputs=[Io("heightmap_path", "string")],
    pre=["dem_downloaded"],
    post=["heightmap_generated"],
    cost=0.3,
    value=0.4,
    can_rerun=True,
)
async def phase1_generate_heightmap(params: Dict[str, Any]) -> Dict[str, Any]:
    """Generate heightmap from DEM."""
    dem_path = params.get("dem_path")
    output_path = params.get("output_path", "/output/heightmap.raw")
    resolution = params.get("resolution", 4096)
    
    # Mock result
    return {
        "heightmap_path": output_path,
        "resolution": resolution,
        "format": "raw16",
        "_mock": True,
    }
