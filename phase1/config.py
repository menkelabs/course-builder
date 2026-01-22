"""
Phase 1 Configuration

Configuration classes for QGIS/GDAL terrain preparation pipeline.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict
import json
import yaml


@dataclass
class QGISConfig:
    """QGIS-specific configuration."""
    qgis_process_path: Optional[str] = None  # Path to qgis_process executable
    template_qgz: Optional[Path] = None  # Template QGIS project file
    default_crs: str = "EPSG:3857"  # Default CRS if not detected


@dataclass
class GDALConfig:
    """GDAL-specific configuration."""
    gdal_translate_path: Optional[str] = None  # Path to gdal_translate
    gdalwarp_path: Optional[str] = None  # Path to gdalwarp
    heightmap_size: int = 4097  # Unity heightmap size
    overlay_size: int = 8192  # Overlay image size
    overlay_quality: int = 95  # JPEG quality for overlays
    overlay_max_zoom: int = 19  # Max zoom for overlay export (PDF recommends 19, default is 20)


@dataclass
class WorkspaceConfig:
    """Workspace directory structure configuration."""
    workspace_path: Path = Path(".")
    dem_dir: Path = field(default_factory=lambda: Path("DEM"))
    shapefiles_dir: Path = field(default_factory=lambda: Path("Shapefiles"))
    tif_dir: Path = field(default_factory=lambda: Path("TIF"))
    heightmap_dir: Path = field(default_factory=lambda: Path("Heightmap"))
    overlays_dir: Path = field(default_factory=lambda: Path("Overlays"))
    runs_dir: Path = field(default_factory=lambda: Path("Runs"))


@dataclass
class LocationConfig:
    """Default location configuration for map positioning."""
    address: Optional[str] = None  # Full address string
    zip_code: Optional[str] = None  # ZIP/postal code
    city: Optional[str] = None  # City name
    state: Optional[str] = None  # State/province
    country: Optional[str] = None  # Country (default: "US")
    center_lat: Optional[float] = None  # Direct latitude coordinate
    center_lon: Optional[float] = None  # Direct longitude coordinate
    zoom_level: int = 15  # Recommended: 15-16 for viewing/drawing boundary (shows full course)
    # Zoom level guide:
    # - 12-13: Very wide view (entire region)
    # - 14-15: Good for seeing full golf course (RECOMMENDED for boundary drawing)
    # - 16-17: Closer view (individual holes visible)
    # - 18-19: Very close (individual features)
    # - 20: Maximum detail (may not be available everywhere)


@dataclass
class InteractiveConfig:
    """Configuration for interactive QGIS selection."""
    enable_interactive: bool = True
    template_qgz: Optional[Path] = None
    boundary_layer_name: str = "Course Boundary"
    selection_timeout: int = 1800  # seconds (30 minutes)
    auto_continue: bool = True  # Continue pipeline after selection
    location: Optional[LocationConfig] = None  # Default location for map positioning


@dataclass
class Phase1Config:
    """Main configuration for Phase 1 pipeline."""
    course_name: str = "Course"
    workspace: WorkspaceConfig = field(default_factory=WorkspaceConfig)
    qgis: QGISConfig = field(default_factory=QGISConfig)
    gdal: GDALConfig = field(default_factory=GDALConfig)
    interactive: InteractiveConfig = field(default_factory=InteractiveConfig)
    location: LocationConfig = field(default_factory=LocationConfig)  # Default location
    geographic_bounds: Optional[Dict[str, float]] = None  # From user selection
    verbose: bool = False
    
    @classmethod
    def from_yaml(cls, path: Path) -> "Phase1Config":
        """Load configuration from YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)
    
    @classmethod
    def from_json(cls, path: Path) -> "Phase1Config":
        """Load configuration from JSON file."""
        with open(path) as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    @classmethod
    def from_dict(cls, data: dict) -> "Phase1Config":
        """Create config from dictionary."""
        workspace = WorkspaceConfig(**data.get("workspace", {}))
        qgis = QGISConfig(**data.get("qgis", {}))
        gdal_data = data.get("gdal", {})
        # Handle overlay_max_zoom if not present (backward compatibility)
        if "overlay_max_zoom" not in gdal_data:
            gdal_data["overlay_max_zoom"] = 19
        gdal = GDALConfig(**gdal_data)
        location = LocationConfig(**data.get("location", {}))
        interactive_data = data.get("interactive", {})
        if "location" in interactive_data:
            interactive_data["location"] = LocationConfig(**interactive_data["location"])
        interactive = InteractiveConfig(**interactive_data)
        
        return cls(
            course_name=data.get("course_name", "Course"),
            workspace=workspace,
            qgis=qgis,
            gdal=gdal,
            interactive=interactive,
            location=location,
            geographic_bounds=data.get("geographic_bounds"),
            verbose=data.get("verbose", False),
        )
    
    def to_yaml(self, path: Path) -> None:
        """Save configuration to YAML file."""
        data = self.to_dict()
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)
    
    def to_json(self, path: Path) -> None:
        """Save configuration to JSON file."""
        data = self.to_dict()
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    
    def to_dict(self) -> dict:
        """Convert config to dictionary."""
        interactive_dict = {
            "enable_interactive": self.interactive.enable_interactive,
            "template_qgz": str(self.interactive.template_qgz) if self.interactive.template_qgz else None,
            "boundary_layer_name": self.interactive.boundary_layer_name,
            "selection_timeout": self.interactive.selection_timeout,
            "auto_continue": self.interactive.auto_continue,
        }
        if self.interactive.location:
            interactive_dict["location"] = {
                "address": self.interactive.location.address,
                "zip_code": self.interactive.location.zip_code,
                "city": self.interactive.location.city,
                "state": self.interactive.location.state,
                "country": self.interactive.location.country,
                "center_lat": self.interactive.location.center_lat,
                "center_lon": self.interactive.location.center_lon,
                "zoom_level": self.interactive.location.zoom_level,
            }
        
        return {
            "course_name": self.course_name,
            "workspace": {
                "workspace_path": str(self.workspace.workspace_path),
                "dem_dir": str(self.workspace.dem_dir),
                "shapefiles_dir": str(self.workspace.shapefiles_dir),
                "tif_dir": str(self.workspace.tif_dir),
                "heightmap_dir": str(self.workspace.heightmap_dir),
                "overlays_dir": str(self.workspace.overlays_dir),
                "runs_dir": str(self.workspace.runs_dir),
            },
            "qgis": {
                "qgis_process_path": self.qgis.qgis_process_path,
                "template_qgz": str(self.qgis.template_qgz) if self.qgis.template_qgz else None,
                "default_crs": self.qgis.default_crs,
            },
            "gdal": {
                "gdal_translate_path": self.gdal.gdal_translate_path,
                "gdalwarp_path": self.gdal.gdalwarp_path,
                "heightmap_size": self.gdal.heightmap_size,
                "overlay_size": self.gdal.overlay_size,
                "overlay_quality": self.gdal.overlay_quality,
            },
            "location": {
                "address": self.location.address,
                "zip_code": self.location.zip_code,
                "city": self.location.city,
                "state": self.location.state,
                "country": self.location.country,
                "center_lat": self.location.center_lat,
                "center_lon": self.location.center_lon,
                "zoom_level": self.location.zoom_level,
            },
            "interactive": interactive_dict,
            "geographic_bounds": self.geographic_bounds,
            "verbose": self.verbose,
        }
