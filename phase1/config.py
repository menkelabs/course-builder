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
class InteractiveConfig:
    """Configuration for interactive QGIS selection."""
    enable_interactive: bool = True
    template_qgz: Optional[Path] = None
    boundary_layer_name: str = "Course Boundary"
    selection_timeout: int = 600  # seconds (10 minutes)
    auto_continue: bool = True  # Continue pipeline after selection


@dataclass
class Phase1Config:
    """Main configuration for Phase 1 pipeline."""
    course_name: str = "Course"
    workspace: WorkspaceConfig = field(default_factory=WorkspaceConfig)
    qgis: QGISConfig = field(default_factory=QGISConfig)
    gdal: GDALConfig = field(default_factory=GDALConfig)
    interactive: InteractiveConfig = field(default_factory=InteractiveConfig)
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
        gdal = GDALConfig(**data.get("gdal", {}))
        interactive = InteractiveConfig(**data.get("interactive", {}))
        
        return cls(
            course_name=data.get("course_name", "Course"),
            workspace=workspace,
            qgis=qgis,
            gdal=gdal,
            interactive=interactive,
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
            "interactive": {
                "enable_interactive": self.interactive.enable_interactive,
                "template_qgz": str(self.interactive.template_qgz) if self.interactive.template_qgz else None,
                "boundary_layer_name": self.interactive.boundary_layer_name,
                "selection_timeout": self.interactive.selection_timeout,
                "auto_continue": self.interactive.auto_continue,
            },
            "geographic_bounds": self.geographic_bounds,
            "verbose": self.verbose,
        }
