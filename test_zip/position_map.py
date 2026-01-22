"""
QGIS Map Positioning Script
Run this in QGIS Python Console to position the map and show layers.
"""

from qgis.core import QgsProject, QgsRectangle, QgsCoordinateReferenceSystem
from qgis.utils import iface

project = QgsProject.instance()

# Ensure Google Satellite layer is visible
google_layer = None
for layer in project.mapLayers().values():
    if layer.name() == "Google Satellite":
        google_layer = layer
        break

if google_layer:
    google_layer.setOpacity(1.0)
    # Refresh the layer
    google_layer.triggerRepaint()
    print("✓ Google Satellite layer made visible")

# Ensure Course Boundary layer is visible
boundary_layer = None
for layer in project.mapLayers().values():
    if layer.name() == "Course Boundary":
        boundary_layer = layer
        break

if boundary_layer:
    boundary_layer.setOpacity(1.0)
    boundary_layer.triggerRepaint()
    print("✓ Course Boundary layer made visible")

# Set map extent
extent = QgsRectangle(
    -118.4144124,
    34.0908026,
    -118.40816240000001,
    34.0970526
)

# Set canvas extent if iface is available (GUI mode)
if iface:
    canvas = iface.mapCanvas()
    canvas.setExtent(extent)
    canvas.refresh()
    print(f"✓ Map positioned to: {lat:.6f}, {lon:.6f} (zoom: {zoom})")
else:
    # Headless mode - set project extent
    project.viewSettings().setDefaultViewExtent(extent)
    print(f"✓ Project extent set to: {lat:.6f}, {lon:.6f} (zoom: {zoom})")

print("Map positioning complete!")
