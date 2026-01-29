"""
QGIS Template Project Creation

Creates QGIS project templates for interactive course boundary selection.
"""

import logging
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)


def create_selection_template(
    output_path: Path,
    course_name: str = "Course Selection",
    crs: str = "EPSG:3857",  # Changed default to EPSG:3857 (Web Mercator) for XYZ tiles
    initial_location: Optional[Dict[str, float]] = None
) -> Path:
    """
    Create a QGIS project template for course boundary selection.
    
    The template includes:
    - Google Satellite XYZ tile layer
    - Bing Aerial XYZ tile layer (optional)
    - Empty boundary layer (polygon, editable)
    - Instructions layer (text annotations)
    - Optional initial map extent/center
    
    Args:
        output_path: Path where to save the .qgz template file
        course_name: Name for the project
        crs: Coordinate reference system (default: EPSG:4326 for WGS84)
        initial_location: Optional dict with 'lat', 'lon', 'zoom' to set initial map position
    
    Returns:
        Path to the created template file
    """
    from .qgis_env import setup_qgis_environment
    setup_qgis_environment()
    
    # Ensure PyQt5.sip is imported before QGIS (required by QGIS)
    try:
        import PyQt5.sip
    except ImportError:
        pass
    
    try:
        from qgis.core import (
            QgsProject,
            QgsVectorLayer,
            QgsRasterLayer,
            QgsCoordinateReferenceSystem,
            QgsVectorFileWriter,
            QgsFields,
            QgsField,
            QgsFeature,
            QgsGeometry,
            QgsPointXY,
            QgsRectangle
        )
        from qgis.PyQt.QtCore import QVariant
    except ImportError as e:
        logger.error(f"Failed to import QGIS modules: {e}")
        logger.error("Make sure QGIS Python bindings are properly configured.")
        raise
    
    # Initialize QGIS application (headless)
    from qgis.core import QgsApplication
    QgsApplication.setPrefixPath('/usr', True)
    qgs = QgsApplication([], False)
    qgs.initQgis()
    
    try:
        project = QgsProject.instance()
        # CRITICAL: For XYZ tiles, project MUST be in EPSG:3857 (Web Mercator)
        # QGIS 3.40.4+ has a bug where XYZ tiles don't display if project CRS doesn't match
        # Always use EPSG:3857 for XYZ tile layers
        project_crs = QgsCoordinateReferenceSystem("EPSG:3857")
        
        # Set CRS multiple ways to ensure it sticks
        project.setCrs(project_crs)
        try:
            # Force write CRS to project file
            project.writeEntry("SpatialRefSys", "/ProjectCrs", project_crs.toWkt())
            # Also set via view settings
            view_settings = project.viewSettings()
            # Ensure CRS is properly configured
        except Exception as e:
            logger.warning(f"Could not fully configure project CRS: {e}")
        
        # Verify CRS was set
        actual_crs = project.crs()
        if actual_crs.authid() != "EPSG:3857":
            logger.error(f"CRITICAL: Project CRS is {actual_crs.authid()}, not EPSG:3857!")
            logger.error("XYZ tiles will not display correctly!")
        else:
            logger.info(f"✓ Project CRS verified: {actual_crs.authid()} (Web Mercator)")
        
        project.setTitle(course_name)
        
        # Add Bing Aerial XYZ layer (no API key required)
        logger.info("Adding Bing Aerial layer...")
        # For QGIS 3.x, use provider type "wms" even for XYZ tiles
        # The URI must contain "type=xyz&url=..." format
        # Bing uses quadkey format {q} instead of {x}/{y}/{z}
        bing_uri = (
            "type=xyz&"
            "url=https://ecn.t3.tiles.virtualearth.net/tiles/a{q}.jpeg?g=1"
        )
        
        # Check if Bing Aerial layer already exists
        existing_bing = None
        for layer_id, layer in project.mapLayers().items():
            if layer.name() == "Bing Aerial":
                existing_bing = layer
                break
        
        if existing_bing:
            logger.info("Bing Aerial layer already exists, skipping duplicate")
            bing_layer = existing_bing
        else:
            # Create XYZ tile layer - MUST use "wms" provider type for QGIS 3.x
            bing_layer = QgsRasterLayer(bing_uri, "Bing Aerial", "wms")
            
            if not bing_layer.isValid():
                error_msg = bing_layer.error().message() if hasattr(bing_layer, 'error') and bing_layer.error() else 'Unknown error'
                logger.error(f"Bing layer failed to load: {error_msg}")
                raise RuntimeError(f"Bing layer failed to load: {error_msg}")
            
            # CRITICAL: Ensure layer CRS matches project CRS (EPSG:3857)
            bing_crs = QgsCoordinateReferenceSystem("EPSG:3857")
            bing_layer.setCrs(bing_crs)
            
            # Verify layer CRS
            layer_crs = bing_layer.crs()
            if layer_crs.authid() != "EPSG:3857":
                logger.warning(f"Bing layer CRS is {layer_crs.authid()}, forcing to EPSG:3857")
                bing_layer.setCrs(bing_crs)
                # Verify again
                layer_crs = bing_layer.crs()
                if layer_crs.authid() != "EPSG:3857":
                    logger.error(f"Failed to set Bing layer CRS to EPSG:3857, got {layer_crs.authid()}")
            
            # Verify project CRS matches
            project_crs_check = project.crs()
            if project_crs_check.authid() != "EPSG:3857":
                logger.error(f"Project CRS mismatch: {project_crs_check.authid()} vs EPSG:3857")
                project.setCrs(bing_crs)
            
            project.addMapLayer(bing_layer)
            
            # Make Bing Aerial visible and on top
            root = project.layerTreeRoot()
            bing_node = root.findLayer(bing_layer.id())
            if bing_node:
                bing_node.setItemVisibilityChecked(True)
                # Move to top of layer stack
                try:
                    parent = bing_node.parent()
                    if parent:
                        cloned = bing_node.clone()
                        parent.insertChildNode(0, cloned)
                        parent.removeChildNode(bing_node)
                except:
                    pass
            
            logger.info(f"✓ Bing Aerial layer added (CRS: {bing_layer.crs().authid()})")
        
        # Ensure Bing Aerial is visible and on top
        if bing_layer:
            bing_layer.setOpacity(1.0)
            root = project.layerTreeRoot()
            layer_node = root.findLayer(bing_layer.id())
            if layer_node:
                layer_node.setItemVisibilityChecked(True)
                # Move to top of layer stack
                try:
                    # Remove and reinsert at top to ensure it's on top
                    parent = layer_node.parent()
                    if parent:
                        cloned = layer_node.clone()
                        parent.insertChildNode(0, cloned)
                        parent.removeChildNode(layer_node)
                except:
                    pass
            logger.info("✓ Bing Aerial layer configured as visible and on top")
        
        
        # Create boundary layer (polygon, editable, in memory)
        # CRITICAL: Boundary layer MUST use same CRS as project (EPSG:3857) for proper display
        logger.info("Creating boundary layer...")
        boundary_layer = QgsVectorLayer(
            f"Polygon?crs=EPSG:3857",  # Match project CRS (Web Mercator)
            "Course Boundary",
            "memory"
        )
        
        # Ensure boundary layer CRS matches project CRS
        boundary_layer.setCrs(project_crs)
        
        # Add fields to boundary layer
        fields = QgsFields()
        fields.append(QgsField("course_name", QVariant.String))
        fields.append(QgsField("area_km2", QVariant.Double))
        boundary_layer.dataProvider().addAttributes(fields)
        boundary_layer.updateFields()
        
        # Memory layers are editable by default, no need to set editable
        # User can start editing directly in QGIS GUI
        
        # Check if boundary layer already exists - if it has wrong CRS, remove it
        existing_boundary = None
        for layer_id, layer in project.mapLayers().items():
            if layer.name() == "Course Boundary":
                existing_boundary = layer
                break
        
        if existing_boundary:
            # Check if existing layer has correct CRS
            if existing_boundary.crs().authid() != "EPSG:3857":
                logger.info(f"Existing boundary layer has wrong CRS ({existing_boundary.crs().authid()}), removing and recreating")
                project.removeMapLayer(existing_boundary.id())
                # Add new layer with correct CRS
                project.addMapLayer(boundary_layer)
                logger.info("✓ Boundary layer recreated with correct CRS (EPSG:3857)")
            else:
                logger.info("Course Boundary layer already exists with correct CRS, reusing")
                boundary_layer = existing_boundary
        else:
            # Add to project
            project.addMapLayer(boundary_layer)
            logger.info("✓ Boundary layer created and added to project")
        
        # Make boundary layer visible and ensure it's in layer tree
        boundary_layer.setOpacity(1.0)
        root = project.layerTreeRoot()
        layer_node = root.findLayer(boundary_layer.id())
        if layer_node:
            layer_node.setItemVisibilityChecked(True)
        logger.info("✓ Boundary layer configured as visible and editable")
        
        # Set initial map extent if location provided
        if initial_location:
            from qgis.core import QgsRectangle, QgsCoordinateReferenceSystem, QgsCoordinateTransform
            lat = initial_location.get('lat')
            lon = initial_location.get('lon')
            zoom = initial_location.get('zoom', 15)
            
            # Calculate extent in Web Mercator (EPSG:3857) for XYZ tiles
            # Convert WGS84 center to Web Mercator
            source_crs = QgsCoordinateReferenceSystem("EPSG:4326")  # WGS84
            dest_crs = QgsCoordinateReferenceSystem("EPSG:3857")  # Web Mercator
            transform = QgsCoordinateTransform(source_crs, dest_crs, project)
            
            # Calculate buffer in degrees first, then transform
            zoom_factor = 0.01 / (2 ** (19 - zoom))
            buffer = zoom_factor * 5  # 5x zoom factor for reasonable view
            
            wgs84_extent = QgsRectangle(
                lon - buffer,
                lat - buffer,
                lon + buffer,
                lat + buffer
            )
            
            # Transform to Web Mercator
            mercator_extent = transform.transformBoundingBox(wgs84_extent)
            
            # Set project's default view extent using QgsReferencedRectangle
            # This ensures map shows tiles when QGIS opens
            # QgsReferencedRectangle is required for setDefaultViewExtent
            try:
                if mercator_extent.width() > 0 and mercator_extent.height() > 0:
                    from qgis.core import QgsReferencedRectangle
                    ref_extent = QgsReferencedRectangle(mercator_extent, dest_crs)
                    view_settings = project.viewSettings()
                    view_settings.setDefaultViewExtent(ref_extent)
                    logger.info(f"✓ Set project default view extent: {lat:.6f}, {lon:.6f} (zoom: {zoom})")
            except (AttributeError, Exception) as e:
                logger.warning(f"Could not set default view extent: {e}")
                # Fallback: try setting project extent directly (without reference)
                try:
                    if mercator_extent.width() > 0 and mercator_extent.height() > 0:
                        project.setExtent(mercator_extent)
                        logger.info(f"✓ Set project extent (fallback): {lat:.6f}, {lon:.6f}")
                except Exception as e2:
                    logger.warning(f"Fallback extent setting also failed: {e2}")
            
            # Store location info in project metadata for scripts
            project.writeEntry("CourseBuilder", "center_lat", str(lat))
            project.writeEntry("CourseBuilder", "center_lon", str(lon))
            project.writeEntry("CourseBuilder", "zoom_level", str(zoom))
            # Default square size: 2000m (user can adjust)
            project.writeEntry("CourseBuilder", "boundary_size", "2000.0")
            logger.info("  A positioning script will be created to fine-tune the map position")
            logger.info("  Location stored in project metadata for auto-boundary creation")
        else:
            # If no initial location, set a default extent in Web Mercator (for XYZ tiles)
            # Use a reasonable default: USA center
            from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsReferencedRectangle
            source_crs = QgsCoordinateReferenceSystem("EPSG:4326")
            dest_crs = QgsCoordinateReferenceSystem("EPSG:3857")
            transform = QgsCoordinateTransform(source_crs, dest_crs, project)
            
            # Default: USA center, reasonable zoom
            default_wgs84 = QgsRectangle(-100, 35, -80, 45)
            default_mercator = transform.transformBoundingBox(default_wgs84)
            
            try:
                if default_mercator.width() > 0 and default_mercator.height() > 0:
                    ref_extent = QgsReferencedRectangle(default_mercator, dest_crs)
                    view_settings = project.viewSettings()
                    view_settings.setDefaultViewExtent(ref_extent)
            except (AttributeError, Exception):
                try:
                    if default_mercator.width() > 0 and default_mercator.height() > 0:
                        project.setExtent(default_mercator)
                except:
                    pass
            logger.info("No initial location provided - map will open at default extent (USA center)")
        
        # Note: setActiveLayer is a GUI method, not needed in headless mode
        # The layer will be available in QGIS when the project is opened
        
        # Add QGIS macro to auto-run scripts when project opens
        if initial_location:
            logger.info("✓ Map will open at specified location")
            # Create macro that runs positioning script automatically
            _add_project_macro(project, output_path.parent)
        
        # Save template
        output_path.parent.mkdir(parents=True, exist_ok=True)
        success = project.write(str(output_path))
        
        if success:
            logger.info(f"✓ Template saved to: {output_path}")
            return output_path
        else:
            raise Exception(f"Failed to save QGIS project to {output_path}")
    
    finally:
        qgs.exitQgis()


def _add_project_macro(project, workspace_path: Path) -> None:
    """
    Add QGIS project macros to auto-run scripts when project opens.
    
    QGIS macros run Python code on project events:
    - openProject(): runs when project opens
    - saveProject(): runs when project saves
    - closeProject(): runs when project closes
    
    Args:
        project: QgsProject instance
        workspace_path: Path to workspace directory containing scripts
    """
    # Get absolute paths to scripts
    position_script = workspace_path / "position_map.py"
    fix_blank_script = workspace_path / "fix_blank_map.py"
    
    # Build macro code that runs when project opens
    # Use raw strings and escape properly for XML storage
    macro_code = f'''
def openProject():
    """Auto-run when QGIS project opens."""
    from qgis.core import QgsProject
    from qgis.utils import iface
    from qgis.PyQt.QtWidgets import QMessageBox
    import os
    
    # Get workspace path from project location
    project = QgsProject.instance()
    project_path = project.absoluteFilePath()
    if project_path:
        workspace = os.path.dirname(project_path)
    else:
        workspace = r"{workspace_path}"
    
    # Scripts to potentially run
    position_script = os.path.join(workspace, "position_map.py")
    fix_blank_script = os.path.join(workspace, "fix_blank_map.py")
    create_boundary_script = os.path.join(workspace, "create_boundary.py")
    
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
    
    # Show instructions to user
    msg = """QGIS Project Loaded!

WORKFLOW:
1. Use mouse wheel to zoom, middle-drag to pan
2. Center the map on your golf course
3. Open Python Console (Ctrl+Alt+P)
4. Run: exec(open(r'""" + create_boundary_script + """').read())
5. Adjust the boundary box as needed
6. Save the Course Boundary layer as shapefile

The script will auto-detect the saved shapefile."""
    
    # Show in QGIS message bar instead of blocking dialog
    if iface:
        iface.messageBar().pushMessage("Course Builder", "Project loaded! See Python Console for instructions.", level=0, duration=10)
        print("=" * 60)
        print(msg)
        print("=" * 60)

def saveProject():
    pass

def closeProject():
    pass
'''
    
    # Enable macros in project settings
    try:
        # Set macro to run on open
        project.writeEntry("Macros", "pythonCode", macro_code)
        # Enable macros (0=never, 1=ask, 2=for this session, 3=always)
        project.writeEntry("Macros", "allowMacros", "3")
        logger.info("✓ Added project macro to auto-run scripts on open")
        logger.info("  NOTE: User may need to enable macros in QGIS Settings -> Options -> General")
    except Exception as e:
        logger.warning(f"Could not add project macro: {e}")
        logger.info("  User will need to run scripts manually from Python Console")


def create_simple_template_script(output_path: Path) -> Path:
    """
    Create a simple Python script that can be run in QGIS Python console
    to set up the project programmatically.
    
    This is an alternative if we can't create the template programmatically.
    """
    script_content = '''"""
QGIS Project Setup Script
Run this in QGIS Python Console to set up course selection project.
"""

from qgis.core import QgsProject, QgsVectorLayer, QgsRasterLayer

project = QgsProject.instance()

# Add Google Satellite
google_url = "type=xyz&url=https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}&zmax=19&zmin=0"
google_layer = QgsRasterLayer(google_url, "Google Satellite", "wms")
if google_layer.isValid():
    project.addMapLayer(google_layer)

# Create boundary layer
boundary_layer = QgsVectorLayer(
    "Polygon?crs=EPSG:4326",
    "Course Boundary",
    "memory"
)
boundary_layer.setEditable(True)
project.addMapLayer(boundary_layer)

print("Project setup complete! Draw your course boundary on the 'Course Boundary' layer.")
'''
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(script_content)
    logger.info(f"✓ Setup script saved to: {output_path}")
    return output_path
