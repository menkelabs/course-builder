"""
Phase 1 Pipeline Client

Main client class that orchestrates the QGIS/GDAL terrain preparation pipeline.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from .config import Phase1Config

logger = logging.getLogger(__name__)


@dataclass
class PipelineState:
    """Current state of the pipeline execution."""
    course_name: str = ""
    workspace_path: Path = Path(".")
    merged_dem: Optional[Path] = None
    inner_heightmap: Optional[Path] = None
    outer_heightmap: Optional[Path] = None
    inner_raw: Optional[Path] = None
    outer_raw: Optional[Path] = None
    overlays: List[Path] = field(default_factory=list)
    completed_stages: List[str] = field(default_factory=list)


class Phase1Client:
    """
    Main client for the Phase 1 terrain preparation pipeline.
    
    The pipeline consists of these stages:
    1. Project Setup (Stage 2)
    2. DEM Tile Merging (Stage 3)
    3. Heightmap Creation and Overlays (Stage 4)
    4. Unity Conversion (Stage 5)
    5. Validation
    
    Usage:
        # Full pipeline
        client = Phase1Client(config)
        client.run()
        
        # Step-by-step
        client = Phase1Client(config)
        client.setup_project()
        client.merge_dem_tiles()
        client.create_heightmaps()
        client.convert_for_unity()
        client.validate()
    """
    
    def __init__(self, config: Optional[Phase1Config] = None):
        """
        Initialize the Phase 1 client.
        
        Args:
            config: Pipeline configuration (uses defaults if None)
        """
        self.config = config or Phase1Config()
        self.state = PipelineState()
        self.state.course_name = self.config.course_name
        self.state.workspace_path = self.config.workspace.workspace_path
        
        # Setup logging
        if self.config.verbose:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)
    
    def interactive_course_selection(self) -> Dict[str, float]:
        """
        Launch QGIS for user to interactively select course boundary.
        
        Returns:
            Dictionary with geographic bounds (northLat, southLat, eastLon, westLon, etc.)
        """
        from .pipeline.interactive_selection import interactive_course_selection_workflow
        
        logger.info("=" * 60)
        logger.info("INTERACTIVE COURSE SELECTION")
        logger.info("=" * 60)
        
        template_path = self.config.interactive.template_qgz
        if template_path:
            template_path = Path(template_path)
        
        bounds = interactive_course_selection_workflow(
            workspace_path=self.state.workspace_path,
            course_name=self.config.course_name,
            template_path=template_path,
            timeout=self.config.interactive.selection_timeout
        )
        
        # Store bounds in config
        self.config.geographic_bounds = bounds
        
        logger.info("=" * 60)
        logger.info("Course boundary selection complete!")
        logger.info(f"Bounds: N:{bounds['northLat']:.6f}, S:{bounds['southLat']:.6f}, "
                   f"E:{bounds['eastLon']:.6f}, W:{bounds['westLon']:.6f}")
        logger.info(f"Area: {bounds['area_km2']:.2f} km²")
        logger.info("=" * 60)
        
        return bounds
    
    def setup_project(self) -> None:
        """Stage 2: Set up QGIS project and workspace structure."""
        logger.info("Stage 2: Setting up project...")
        
        # If we have geographic bounds, use them for project setup
        if self.config.geographic_bounds:
            logger.info(f"Using geographic bounds from selection: {self.config.geographic_bounds}")
        
        # TODO: Implement project setup with bounds
        self.state.completed_stages.append("setup_project")
        logger.info("Project setup complete")
    
    def merge_dem_tiles(self, dem_paths: List[Path]) -> Path:
        """Stage 3: Merge DEM tiles into single TIF."""
        logger.info("Stage 3: Merging DEM tiles...")
        # TODO: Implement DEM merging
        merged_path = self.config.workspace.tif_dir / f"{self.config.course_name}_merged.tif"
        self.state.merged_dem = merged_path
        self.state.completed_stages.append("merge_dem_tiles")
        logger.info(f"Merged DEM saved to {merged_path}")
        return merged_path
    
    def create_heightmaps(self) -> tuple[Path, Path]:
        """Stage 4: Create inner and outer heightmaps."""
        logger.info("Stage 4: Creating heightmaps...")
        # TODO: Implement heightmap creation
        inner_path = self.config.workspace.heightmap_dir / "INNER" / f"{self.config.course_name}_Lidar_Surface_Inner.tif"
        outer_path = self.config.workspace.heightmap_dir / "OUTER" / f"{self.config.course_name}_Lidar_Surface_Outer.tif"
        self.state.inner_heightmap = inner_path
        self.state.outer_heightmap = outer_path
        self.state.completed_stages.append("create_heightmaps")
        logger.info("Heightmaps created")
        return inner_path, outer_path
    
    def convert_for_unity(self) -> tuple[Path, Path]:
        """Stage 5: Convert heightmaps to Unity RAW format."""
        logger.info("Stage 5: Converting for Unity...")
        # TODO: Implement Unity conversion
        inner_raw = self.state.inner_heightmap.with_suffix(".raw") if self.state.inner_heightmap else None
        outer_raw = self.state.outer_heightmap.with_suffix(".raw") if self.state.outer_heightmap else None
        self.state.inner_raw = inner_raw
        self.state.outer_raw = outer_raw
        self.state.completed_stages.append("convert_for_unity")
        logger.info("Unity conversion complete")
        return inner_raw, outer_raw
    
    def validate(self) -> bool:
        """Validate pipeline output."""
        logger.info("Validating output...")
        # TODO: Implement validation
        checks = {
            "Merged DEM exists": self.state.merged_dem and self.state.merged_dem.exists() if self.state.merged_dem else False,
            "Inner heightmap exists": self.state.inner_heightmap and self.state.inner_heightmap.exists() if self.state.inner_heightmap else False,
            "Outer heightmap exists": self.state.outer_heightmap and self.state.outer_heightmap.exists() if self.state.outer_heightmap else False,
            "Inner RAW exists": self.state.inner_raw and self.state.inner_raw.exists() if self.state.inner_raw else False,
            "Outer RAW exists": self.state.outer_raw and self.state.outer_raw.exists() if self.state.outer_raw else False,
        }
        
        all_passed = all(checks.values())
        for check, passed in checks.items():
            status = "✓" if passed else "✗"
            logger.info(f"  {status} {check}")
        
        return all_passed
    
    def run(self, interactive: bool = True) -> PipelineState:
        """
        Run the complete Phase 1 pipeline.
        
        Args:
            interactive: If True and no bounds exist, launch interactive selection
        """
        logger.info("Running complete Phase 1 pipeline...")
        
        # Step 1: Interactive selection (if enabled and no bounds)
        if interactive and self.config.interactive.enable_interactive:
            if not self.config.geographic_bounds:
                logger.info("No geographic bounds found. Starting interactive selection...")
                self.interactive_course_selection()
            else:
                logger.info("Using existing geographic bounds from config")
        
        # Step 2: Project setup
        self.setup_project()
        
        # TODO: Continue with automated processing
        # Step 3: DEM merging (using bounds to find appropriate tiles)
        # if self.config.geographic_bounds:
        #     dem_paths = self._find_dem_tiles_for_bounds(self.config.geographic_bounds)
        #     self.merge_dem_tiles(dem_paths)
        
        # Step 4: Heightmap creation
        # self.create_heightmaps()
        
        # Step 5: Unity conversion
        # self.convert_for_unity()
        
        # Step 6: Validation
        # self.validate()
        
        logger.info("Pipeline complete!")
        return self.state
