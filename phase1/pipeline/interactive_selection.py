"""
Interactive Course Selection

Launch QGIS GUI for user to visually select course boundary,
then monitor for user completion and extract coordinates.
"""

import logging
import subprocess
import time
import shutil
import os
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)


def launch_qgis_with_template(
    template_path: Path,
    workspace_path: Path,
    course_name: str = "Course Selection"
) -> Path:
    """
    Launch QGIS GUI with a template project for course selection.
    
    Args:
        template_path: Path to QGIS template project (.qgz)
        workspace_path: Workspace directory where project will be copied
        course_name: Name for the course/project
    
    Returns:
        Path to the QGIS project file in workspace
    """
    workspace_path.mkdir(parents=True, exist_ok=True)
    
    # Copy template to workspace
    project_path = workspace_path / f"{course_name}_selection.qgz"
    
    if template_path.exists():
        shutil.copy(template_path, project_path)
        logger.info(f"Template copied to: {project_path}")
    else:
        logger.warning(f"Template not found at {template_path}, creating new project")
        # Create a minimal project if template doesn't exist
        project_path = _create_minimal_project(project_path, course_name)
    
    # Launch QGIS
    logger.info("Launching QGIS...")
    try:
        # Try to find qgis executable
        qgis_cmd = _find_qgis_executable()
        
        # Set environment variables so QGIS can find Python bindings
        env = os.environ.copy()
        dist_packages = "/usr/lib/python3/dist-packages"
        
        # Add dist-packages to PYTHONPATH
        if 'PYTHONPATH' in env:
            if dist_packages not in env['PYTHONPATH']:
                env['PYTHONPATH'] = dist_packages + os.pathsep + env['PYTHONPATH']
        else:
            env['PYTHONPATH'] = dist_packages
        
        # Also set QGIS_PREFIX_PATH if not set
        if 'QGIS_PREFIX_PATH' not in env:
            env['QGIS_PREFIX_PATH'] = '/usr'
        
        logger.debug(f"PYTHONPATH set to: {env.get('PYTHONPATH')}")
        
        subprocess.Popen(
            [qgis_cmd, str(project_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env
        )
        logger.info(f"✓ QGIS launched with project: {project_path}")
        logger.info("")
        logger.info("=" * 60)
        logger.info("INSTRUCTIONS FOR USER:")
        logger.info("=" * 60)
        logger.info("1. Navigate to the golf course location in QGIS")
        logger.info("2. Use the 'Add Polygon Feature' tool to draw around the course")
        logger.info("3. Draw a polygon covering the entire golf course area")
        logger.info("4. Save the 'Course Boundary' layer when finished")
        logger.info("5. Close QGIS or the script will continue automatically")
        logger.info("=" * 60)
        logger.info("")
        
        return project_path
    
    except FileNotFoundError:
        logger.error("QGIS executable not found!")
        logger.error("Please install QGIS Desktop or ensure 'qgis' is in your PATH")
        raise
    except Exception as e:
        logger.error(f"Failed to launch QGIS: {e}")
        raise


def _find_qgis_executable() -> str:
    """Find QGIS executable path."""
    # Check for wrapper script first (sets PYTHONPATH)
    wrapper_path = Path.home() / ".local" / "bin" / "qgis"
    if wrapper_path.exists() and wrapper_path.is_file():
        logger.debug(f"Using QGIS wrapper: {wrapper_path}")
        return str(wrapper_path)
    
    # Common locations
    possible_paths = [
        "qgis",
        "/usr/bin/qgis",
        "/usr/local/bin/qgis",
        "/Applications/QGIS.app/Contents/MacOS/QGIS",  # macOS
    ]
    
    for path in possible_paths:
        try:
            result = subprocess.run(
                ["which", path] if "/" not in path else ["test", "-f", path],
                capture_output=True,
                check=True
            )
            if "/" not in path:
                return path
            elif Path(path).exists():
                return path
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    
    # If not found, try 'qgis' and let it fail with clear error
    return "qgis"


def _create_minimal_project(project_path: Path, course_name: str) -> Path:
    """Create a minimal QGIS project if template doesn't exist."""
    # For now, just create an empty file
    # User will need to manually add layers in QGIS
    project_path.parent.mkdir(parents=True, exist_ok=True)
    project_path.touch()
    logger.warning("Created empty project file. User will need to add layers manually.")
    return project_path


def _create_minimal_qgz(project_path: Path, course_name: str) -> Path:
    """Create a minimal .qgz file (QGIS project is a ZIP archive)."""
    import zipfile
    
    project_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Minimal QGIS project XML
    minimal_xml = f"""<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="3.40.14-Bratislava" styleCategories="AllStyleCategories">
  <flags>
    <Identifiable>1</Identifiable>
    <Removable>1</Removable>
    <Searchable>1</Searchable>
    <Private>0</Private>
  </flags>
  <title>{course_name}</title>
  <projectCrs>
    <spatialrefsys>
      <wkt>GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]</wkt>
      <proj4>+proj=longlat +datum=WGS84 +no_defs</proj4>
      <srsid>3452</srsid>
      <srid>4326</srid>
      <authid>EPSG:4326</authid>
      <description>WGS 84</description>
      <projectionacronym>longlat</projectionacronym>
      <ellipsoidacronym>EPSG:7030</ellipsoidacronym>
      <geographicflag>1</geographicflag>
    </spatialrefsys>
  </projectCrs>
  <layerTreeGroup>
    <customproperties/>
  </layerTreeGroup>
</qgis>
"""
    
    # Create .qgz (ZIP) file
    with zipfile.ZipFile(project_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("project.qgs", minimal_xml)
    
    logger.info(f"Created minimal QGIS project: {project_path}")
    return project_path


def wait_for_boundary_shapefile(
    workspace_path: Path,
    boundary_filename: str = "Course_Boundary.shp",
    timeout: int = 600,
    check_interval: int = 2
) -> Optional[Path]:
    """
    Wait for user to save boundary shapefile.
    
    Polls the workspace Shapefiles directory for the boundary file.
    
    Args:
        workspace_path: Workspace directory
        boundary_filename: Expected filename for boundary shapefile
        timeout: Maximum time to wait in seconds (default: 10 minutes)
        check_interval: How often to check for file (seconds)
    
    Returns:
        Path to boundary shapefile when found, None if timeout
    """
    shapefiles_dir = workspace_path / "Shapefiles"
    shapefiles_dir.mkdir(parents=True, exist_ok=True)
    
    boundary_path = shapefiles_dir / boundary_filename
    
    logger.info(f"Waiting for boundary file: {boundary_path}")
    logger.info(f"Timeout: {timeout} seconds (checking every {check_interval}s)")
    
    start_time = time.time()
    last_log_time = start_time
    
    while True:
        elapsed = time.time() - start_time
        
        # Check if file exists
        if boundary_path.exists():
            # Verify it's a valid shapefile (has .shp, .shx, .dbf)
            required_files = [
                boundary_path,
                boundary_path.with_suffix('.shx'),
                boundary_path.with_suffix('.dbf'),
            ]
            
            if all(f.exists() for f in required_files):
                logger.info(f"✓ Boundary file detected: {boundary_path}")
                return boundary_path
        
        # Check timeout
        if elapsed >= timeout:
            logger.warning(f"Timeout waiting for boundary file after {timeout} seconds")
            return None
        
        # Log progress every 30 seconds
        if time.time() - last_log_time >= 30:
            logger.info(f"Still waiting... ({int(elapsed)}s elapsed)")
            last_log_time = time.time()
        
        time.sleep(check_interval)


def wait_for_boundary_in_project(
    project_path: Path,
    layer_name: str = "Course Boundary",
    timeout: int = 600,
    check_interval: int = 5
) -> Optional[Dict]:
    """
    Wait for user to add boundary to QGIS project layer.
    
    NOTE: This method uses QGIS Python bindings which can cause segfaults
    in some environments. The shapefile approach is preferred.
    
    Args:
        project_path: Path to QGIS project file
        layer_name: Name of boundary layer
        timeout: Maximum time to wait
        check_interval: How often to check
    
    Returns:
        Bounds dictionary if found, None if timeout
    """
    logger.warning("Project monitoring disabled due to stability issues.")
    logger.info("Please save the boundary as a shapefile instead:")
    logger.info("  1. Right-click 'Course Boundary' layer in QGIS")
    logger.info("  2. Select 'Export' -> 'Save Features As...'")
    logger.info("  3. Choose ESRI Shapefile format")
    logger.info("  4. Save to: workspace/Shapefiles/Course_Boundary.shp")
    return None
    
    # Disabled - causes segfaults
    # from .boundary_extraction import extract_bounds_from_qgis_project
    # ... rest of implementation disabled


def interactive_course_selection_workflow(
    workspace_path: Path,
    course_name: str,
    template_path: Optional[Path] = None,
    timeout: int = 600
) -> Dict[str, float]:
    """
    Complete interactive selection workflow.
    
    1. Launch QGIS with template
    2. Wait for user to draw boundary
    3. Extract bounds
    4. Return bounds dictionary
    
    Args:
        workspace_path: Workspace directory
        course_name: Name of the course
        template_path: Optional path to QGIS template (auto-created if None)
        timeout: Maximum time to wait for user selection
    
    Returns:
        Dictionary with geographic bounds
    """
    from .boundary_extraction import (
        extract_bounds_from_shapefile,
        validate_bounds,
        save_bounds_to_json
    )
    
    # Create template if needed
    if template_path is None:
        template_path = workspace_path / "template_selection.qgz"
        if not template_path.exists():
            logger.info("Creating QGIS template...")
            # Try Python bindings first, fall back to simple template if it fails
            try:
                from .qgis_template import create_selection_template
                create_selection_template(template_path, course_name)
                logger.info("✓ Template created with Python bindings")
            except (ImportError, Exception) as e:
                logger.warning(f"Could not create template with Python bindings: {e}")
                logger.info("Creating minimal template instead (this is OK - QGIS GUI will work fine)...")
                # Create a setup script that user can optionally run in QGIS Python console
                setup_script = template_path.parent / "setup_qgis_project.py"
                from .qgis_template import create_simple_template_script
                create_simple_template_script(setup_script)
                # Create minimal empty project
                _create_minimal_qgz(template_path, course_name)
                logger.info("")
                logger.info("NOTE: If you see SIP errors in QGIS, that's OK!")
                logger.info("The QGIS GUI will still work for drawing boundaries.")
                logger.info("You can optionally run the setup script in QGIS Python console if needed.")
                logger.info(f"Setup script: {setup_script}")
                logger.info("")
    
    # Launch QGIS
    project_path = launch_qgis_with_template(
        template_path,
        workspace_path,
        course_name
    )
    
    # Wait for boundary (try shapefile first, then project)
    logger.info("Waiting for user to save boundary...")
    
    boundary_path = wait_for_boundary_shapefile(
        workspace_path,
        timeout=timeout
    )
    
    if boundary_path:
        # Extract from shapefile
        bounds = extract_bounds_from_shapefile(boundary_path)
    else:
        # Try extracting from project
        logger.info("Shapefile not found, trying to extract from QGIS project...")
        bounds = wait_for_boundary_in_project(project_path, timeout=timeout)
        
        if not bounds:
            raise TimeoutError(
                f"User did not complete boundary selection within {timeout} seconds. "
                "Please save the boundary layer in QGIS."
            )
    
    # Validate bounds
    is_valid, error = validate_bounds(bounds)
    if not is_valid:
        raise ValueError(f"Invalid bounds: {error}")
    
    # Save bounds to JSON for Java backend
    bounds_json_path = workspace_path / "course_bounds.json"
    save_bounds_to_json(bounds, bounds_json_path)
    
    logger.info("✓ Course boundary selection complete!")
    return bounds
