"""
QGIS Template Project Creation

Creates QGIS project templates for interactive course boundary selection.
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def create_selection_template(
    output_path: Path,
    course_name: str = "Course Selection",
    crs: str = "EPSG:4326"
) -> Path:
    """
    Create a QGIS project template for course boundary selection.
    
    The template includes:
    - Google Satellite XYZ tile layer
    - Bing Aerial XYZ tile layer (optional)
    - Empty boundary layer (polygon, editable)
    - Instructions layer (text annotations)
    
    Args:
        output_path: Path where to save the .qgz template file
        course_name: Name for the project
        crs: Coordinate reference system (default: EPSG:4326 for WGS84)
    
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
            QgsPointXY
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
        project.setCrs(QgsCoordinateReferenceSystem(crs))
        project.setTitle(course_name)
        
        # Add Google Satellite XYZ layer
        logger.info("Adding Google Satellite layer...")
        google_url = (
            "type=xyz&url=https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"
            "&zmax=19&zmin=0"
        )
        google_layer = QgsRasterLayer(google_url, "Google Satellite", "wms")
        if google_layer.isValid():
            project.addMapLayer(google_layer)
            logger.info("✓ Google Satellite layer added")
        else:
            logger.warning("Failed to add Google Satellite layer")
        
        # Add Bing Aerial XYZ layer (optional, as backup)
        logger.info("Adding Bing Aerial layer...")
        bing_url = (
            "type=xyz&url=https://ecn.t0.tiles.virtualearth.net/tiles/a{q}.jpeg"
            "?g=1&key=INSERT_YOUR_KEY"
            "&zmax=19&zmin=0"
        )
        # Note: Bing requires API key, so we'll skip it for now
        # Users can add their own if needed
        
        # Create boundary layer (polygon, editable, in memory)
        logger.info("Creating boundary layer...")
        boundary_layer = QgsVectorLayer(
            f"Polygon?crs={crs}",
            "Course Boundary",
            "memory"
        )
        
        # Add fields to boundary layer
        fields = QgsFields()
        fields.append(QgsField("course_name", QVariant.String))
        fields.append(QgsField("area_km2", QVariant.Double))
        boundary_layer.dataProvider().addAttributes(fields)
        boundary_layer.updateFields()
        
        # Memory layers are editable by default, no need to set editable
        # User can start editing directly in QGIS GUI
        
        # Add to project
        project.addMapLayer(boundary_layer)
        logger.info("✓ Boundary layer created and added to project")
        
        # Note: setActiveLayer is a GUI method, not needed in headless mode
        # The layer will be available in QGIS when the project is opened
        
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
