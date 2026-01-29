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
        logger.info("")
        logger.info("=" * 60)
        logger.info("QGIS PROJECT WITH AUTO-RUN MACROS")
        logger.info("=" * 60)
        logger.info("")
        logger.info("📋 MACROS SHOULD AUTO-RUN when QGIS opens!")
        logger.info("   - fix_blank_map.py (fixes XYZ tile display)")
        logger.info("   - position_map.py (centers on golf course)")
        logger.info("")
        logger.info("⚙️  IF MACROS DON'T RUN (map not positioned):")
        logger.info("   Go to: Settings -> Options -> General")
        logger.info("   Set 'Enable macros' to 'Always' or 'Ask'")
        logger.info("   Then close and reopen the project")
        logger.info("")
        
        # Copy fix blank map script (based on research)
        fix_script = workspace_path / "fix_blank_map.py"
        from shutil import copy
        fix_script_path = Path(__file__).parent / "fix_blank_map.py"
        if fix_script_path.exists():
            copy(fix_script_path, fix_script)
            logger.info("⚠ IF MAP IS STILL BLANK (manual fallback):")
            logger.info(f"   Open QGIS Python Console (Plugins -> Python Console or Ctrl+Alt+P)")
            logger.info(f"   Run: exec(open(r'{fix_script}').read())")
            logger.info("")
        
        # Copy helper scripts to workspace
        auto_boundary_script = workspace_path / "create_square_boundary.py"
        auto_boundary_script_path = Path(__file__).parent / "create_square_boundary.py"
        if auto_boundary_script_path.exists():
            copy(auto_boundary_script_path, auto_boundary_script)
        
        diagnostic_script = workspace_path / "test_qgis_tiles.py"
        test_script_path = Path(__file__).parent / "test_qgis_tiles.py"
        if test_script_path.exists() and not diagnostic_script.exists():
            copy(test_script_path, diagnostic_script)
        
        # Show streamlined workflow instructions
        create_boundary_script = workspace_path / "create_boundary.py"
        logger.info("")
        logger.info("🎯 WORKFLOW:")
        logger.info("")
        logger.info("   1. WAIT for macros to auto-position the map on your course")
        logger.info("      (Map should center on your golf course automatically)")
        logger.info("")
        logger.info("   2. EXPLORE: Use MOUSE WHEEL to zoom, MIDDLE DRAG to pan")
        logger.info("      Center the map exactly where you want the boundary")
        logger.info("")
        if create_boundary_script.exists():
            logger.info("   3. CREATE BOUNDARY: Open Python Console (Ctrl+Alt+P) and run:")
            logger.info(f"      exec(open(r'{create_boundary_script}').read())")
            logger.info("      This creates a 2100m square at the CURRENT map center")
        else:
            logger.info("   3. CREATE BOUNDARY: Open Python Console (Ctrl+Alt+P) and run:")
            logger.info(f"      exec(open(r'{auto_boundary_script}').read())")
            logger.info("      This creates a 2000m square boundary")
        logger.info("")
        logger.info("   4. ADJUST: Drag the box or press V for Vertex Tool to resize")
        logger.info("")
        logger.info("   5. SAVE: Right-click 'Course Boundary' -> Export -> Save Features As...")
        logger.info(f"      Save to: {workspace_path / 'Shapefiles' / 'Course_Boundary.shp'}")
        logger.info("")
        logger.info("   📏 Boundary should be SQUARE (same width × height for Unity heightmap)")
        logger.info("")
        logger.info("The script will automatically detect when you save the shapefile.")
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


def _create_boundary_script(script_path: Path, initial_location: dict) -> Path:
    """
    Create a boundary creation script with coordinates baked in.
    This avoids relying on project metadata which may not persist.
    The script will transform coordinates using QGIS's own functions.
    """
    lat = initial_location.get('lat', 40.667975)
    lon = initial_location.get('lon', -74.893919)
    zoom = initial_location.get('zoom', 15)
    
    # Size in meters (2100m = 2000m + 100m buffer)
    half_size = 1050
    
    script_content = f'''"""
Auto-generated boundary creation script.
Default coordinates: {lat}, {lon}
Run this in QGIS Python Console to create the boundary polygon.

The boundary will be created at the CURRENT MAP CENTER - 
zoom/pan to position the map first, then run this script!
"""

from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsFeature,
    QgsGeometry,
    QgsRectangle,
    QgsPointXY,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFillSymbol,
    QgsSingleSymbolRenderer
)

half_size = {half_size}  # meters (2100m total = 2000m + 100m buffer)

project = QgsProject.instance()
project_crs = project.crs()
print("Project CRS:", project_crs.authid())

# Get the CURRENT map canvas center (where user has zoomed/panned to)
canvas = iface.mapCanvas()
center_proj = canvas.center()

print(f"Creating boundary at CURRENT MAP CENTER:")
print(f"  Center in {{project_crs.authid()}}: {{center_proj.x():.2f}}, {{center_proj.y():.2f}}")

# Convert to WGS84 for display
wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
transform_to_wgs84 = QgsCoordinateTransform(project_crs, wgs84, project)
center_wgs84 = transform_to_wgs84.transform(center_proj)
print(f"  Center in WGS84: {{center_wgs84.y():.6f}}, {{center_wgs84.x():.6f}}")

# Calculate bounding box in project CRS
xmin = center_proj.x() - half_size
xmax = center_proj.x() + half_size
ymin = center_proj.y() - half_size
ymax = center_proj.y() + half_size

print(f"BBox: {{xmin:.2f}}, {{ymin:.2f}} to {{xmax:.2f}}, {{ymax:.2f}}")

# Remove existing Course Boundary layer if it exists
for layer in list(project.mapLayers().values()):
    if "Course Boundary" in layer.name():
        print(f"Removing existing layer: {{layer.name()}}")
        project.removeMapLayer(layer.id())

# Create memory layer with project CRS
bbox_layer = QgsVectorLayer(f"Polygon?crs={{project_crs.authid()}}", "Course Boundary", "memory")
if not bbox_layer.isValid():
    raise RuntimeError("Failed to create memory layer")

prov = bbox_layer.dataProvider()

# Create rectangle and add feature
rect = QgsRectangle(xmin, ymin, xmax, ymax)
feat = QgsFeature()
feat.setGeometry(QgsGeometry.fromRect(rect))
prov.addFeatures([feat])
bbox_layer.updateExtents()

# Style: TRANSPARENT fill, red outline
from qgis.PyQt.QtGui import QColor
symbol = QgsFillSymbol.createSimple({{
    "color": "255,255,255,0",
    "outline_color": "255,0,0",
    "outline_width": "2",
    "outline_style": "solid"
}})
symbol.setColor(QColor(0, 0, 0, 0))  # Force transparent
bbox_layer.setRenderer(QgsSingleSymbolRenderer(symbol))

# Add to project (addMapLayer with True adds to legend)
project.addMapLayer(bbox_layer, True)

# Ensure layer is visible
root = project.layerTreeRoot()
node = root.findLayer(bbox_layer.id())
if node:
    node.setItemVisibilityChecked(True)
    print(f"Layer node found and set visible")

# Make vertex markers bigger for easier editing
from qgis.core import QgsSettings
settings = QgsSettings()
settings.setValue("/qgis/digitizing/marker_size_mm", 5.0)
settings.setValue("/qgis/digitizing/marker_size", 5)

# Set as active layer and enable editing
iface.setActiveLayer(bbox_layer)
bbox_layer.startEditing()

# Zoom to boundary
try:
    iface.mapCanvas().setExtent(bbox_layer.extent())
    iface.mapCanvas().refresh()
    
    # Show Advanced Digitizing Toolbar and activate Move Feature tool
    try:
        adv_toolbar = iface.advancedDigitizeToolBar()
        if adv_toolbar:
            adv_toolbar.show()
    except:
        pass
    
    # Enable wheel zoom for map navigation independent of the box
    canvas = iface.mapCanvas()
    canvas.setWheelFactor(2.0)  # Standard zoom factor
    canvas.enableAntiAliasing(True)
    
    # Activate Move Feature tool (for moving the entire polygon)
    try:
        iface.actionMoveFeature().trigger()
    except:
        # Fallback to vertex tool if move feature not available
        iface.actionVertexTool().trigger()
except NameError:
    print("iface not found. Layer still created.")

print("=" * 50)
print("Boundary created at current map center!")
print(f"Size: {{half_size * 2}}m x {{half_size * 2}}m (includes buffer)")
print(f"Extent: {{bbox_layer.extent().toString()}}")
print("=" * 50)
print("")
print("NEXT STEPS:")
print("  1. DRAG the box to reposition it over the course")
print("  2. Press V for Vertex Tool to resize/reshape corners")
print("  3. Use MOUSE WHEEL to zoom in/out for detail")
print("  4. Use MIDDLE MOUSE or SPACE+DRAG to pan")
print("")
print("When done, save the boundary layer as a shapefile.")
'''
    
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(script_content)
    return script_path


def _create_minimal_qgz(project_path: Path, course_name: str, workspace_path: Path = None) -> Path:
    """Create a minimal .qgz file (QGIS project is a ZIP archive) with macros enabled."""
    import zipfile
    
    project_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Get workspace path for macro scripts
    if workspace_path is None:
        workspace_path = project_path.parent
    
    # Build macro code
    macro_code = _build_macro_code(workspace_path)
    
    # Minimal QGIS project XML with macros enabled
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
  <properties>
    <Macros>
      <pythonCode>{_escape_xml(macro_code)}</pythonCode>
    </Macros>
  </properties>
</qgis>
"""
    
    # Create .qgz (ZIP) file
    with zipfile.ZipFile(project_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("project.qgs", minimal_xml)
    
    logger.info(f"Created minimal QGIS project with macros: {project_path}")
    return project_path


def _escape_xml(text: str) -> str:
    """Escape special characters for XML."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _build_macro_code(workspace_path: Path) -> str:
    """Build the Python macro code for QGIS project."""
    workspace_str = str(workspace_path).replace("\\", "/")
    
    return f'''
def openProject():
    """Auto-run when QGIS project opens."""
    from qgis.core import QgsProject
    from qgis.utils import iface
    import os
    
    # Get workspace path from project location
    project = QgsProject.instance()
    project_path = project.absoluteFilePath()
    if project_path:
        workspace = os.path.dirname(project_path)
    else:
        workspace = r"{workspace_str}"
    
    # Scripts to potentially run
    position_script = os.path.join(workspace, "position_map.py")
    fix_blank_script = os.path.join(workspace, "fix_blank_map.py")
    
    # First, run fix_blank_map if it exists (fixes XYZ tile display issues)
    if os.path.exists(fix_blank_script):
        try:
            exec(open(fix_blank_script).read())
            print("Ran fix_blank_map.py")
        except Exception as e:
            print(f"Error running fix_blank_map.py: {{e}}")
    
    # Then run position_map to center on the golf course
    if os.path.exists(position_script):
        try:
            exec(open(position_script).read())
            print("Ran position_map.py")
        except Exception as e:
            print(f"Error running position_map.py: {{e}}")
    
    # Show message in QGIS
    if iface:
        create_boundary_script = os.path.join(workspace, "create_boundary.py")
        iface.messageBar().pushMessage(
            "Course Builder", 
            "Project loaded! Run create_boundary.py from Python Console (Ctrl+Alt+P) when ready.", 
            level=0, duration=15
        )
        print("=" * 60)
        print("QGIS Project Loaded!")
        print("")
        print("WORKFLOW:")
        print("1. Use mouse wheel to zoom, middle-drag to pan")
        print("2. Center the map on your golf course") 
        print("3. Open Python Console (Ctrl+Alt+P)")
        print(f"4. Run: exec(open(r'{{create_boundary_script}}').read())")
        print("5. Adjust the boundary box as needed")
        print("6. Save the Course Boundary layer as shapefile")
        print("=" * 60)

def saveProject():
    pass

def closeProject():
    pass
'''


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
    timeout: int = 1800,
    initial_location: Optional[Dict[str, float]] = None
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
        timeout: Maximum time to wait for user selection (default: 1800 = 30 minutes)
        initial_location: Optional dict with 'lat', 'lon', 'zoom' to set initial map position
    
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
                create_selection_template(template_path, course_name, initial_location=initial_location)
                logger.info("✓ Template created with Python bindings")
                if initial_location:
                    logger.info(f"  Initial location: {initial_location['lat']:.6f}, {initial_location['lon']:.6f}")
                    # Create positioning script that will run in QGIS
                    positioning_script = template_path.parent / "position_map.py"
                    from .qgis_template_fix import create_map_positioning_script
                    create_map_positioning_script(positioning_script, initial_location=initial_location)
                    logger.info(f"  ✓ Created positioning script: {positioning_script}")
                    
                    # Create boundary creation script with coordinates baked in
                    boundary_script = template_path.parent / "create_boundary.py"
                    _create_boundary_script(boundary_script, initial_location)
                    logger.info(f"  ✓ Created boundary script: {boundary_script}")
            except (ImportError, Exception) as e:
                logger.warning(f"Could not create template with Python bindings: {e}")
                logger.info("Creating minimal template instead (this is OK - QGIS GUI will work fine)...")
                # Create a setup script that user can optionally run in QGIS Python console
                setup_script = template_path.parent / "setup_qgis_project.py"
                from .qgis_template import create_simple_template_script
                create_simple_template_script(setup_script)
                
                # Also create map positioning script
                positioning_script = template_path.parent / "position_map.py"
                from .qgis_template_fix import create_map_positioning_script
                create_map_positioning_script(positioning_script, initial_location=initial_location)
                
                # Create minimal empty project with macros enabled
                _create_minimal_qgz(template_path, course_name, workspace_path=template_path.parent)
                logger.info("")
                logger.info("NOTE: If you see SIP errors in QGIS, that's OK!")
                logger.info("The QGIS GUI will still work for drawing boundaries.")
                logger.info("")
                logger.info("If layers are not visible or map is not positioned:")
                logger.info(f"  1. Open QGIS Python Console (Plugins -> Python Console)")
                logger.info(f"  2. Run: exec(open('{positioning_script}').read())")
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
