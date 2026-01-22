"""
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
