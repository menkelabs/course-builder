"""
QGIS Map Positioning Script
Run this in QGIS Python Console to position the map and show layers.
Or it will run automatically when QGIS opens (if added to startup).
"""

from qgis.core import QgsProject
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
    google_layer.triggerRepaint()
    # Make sure it's in the layer tree and visible
    root = project.layerTreeRoot()
    layer_node = root.findLayer(google_layer.id())
    if layer_node:
        layer_node.setItemVisibilityChecked(True)
    print("✓ Google Satellite layer made visible")
else:
    print("⚠ Google Satellite layer not found")

# Ensure Course Boundary layer is visible
boundary_layer = None
for layer in project.mapLayers().values():
    if layer.name() == "Course Boundary":
        boundary_layer = layer
        break

if boundary_layer:
    boundary_layer.setOpacity(1.0)
    boundary_layer.triggerRepaint()
    # Make sure it's in the layer tree and visible
    root = project.layerTreeRoot()
    layer_node = root.findLayer(boundary_layer.id())
    if layer_node:
        layer_node.setItemVisibilityChecked(True)
    print("✓ Course Boundary layer made visible")
else:
    print("⚠ Course Boundary layer not found")

# Set map extent and position
from qgis.core import QgsRectangle, QgsPointXY

zoom_factor = 0.01 / (2 ** (19 - 15))
buffer = zoom_factor * 5

extent = QgsRectangle(
    -121.9490698,
    36.586405500000005,
    -121.94281980000001,
    36.5926555
)

# Set canvas extent if iface is available (GUI mode)
if iface:
    canvas = iface.mapCanvas()
    try:
        # Set extent
        canvas.setExtent(extent)
        canvas.refresh()
        print(f"✓ Map positioned to: {lat:.6f}, {lon:.6f} (zoom: {zoom})")
    except Exception as e:
        # Fallback: use center point and zoom
        print(f"Using center point method (extent failed: {e})")
        canvas.setCenter(QgsPointXY(-121.9459448, 36.5895305))
        # Approximate zoom based on zoom level
        # Zoom level 15 ≈ scale 1:50000, level 16 ≈ 1:25000, etc.
        scale = 50000 / (2 ** (15 - 15))
        canvas.zoomScale(int(scale))
        canvas.refresh()
        print(f"✓ Map centered at: {lat:.6f}, {lon:.6f} (zoom: {zoom})")
else:
    # Headless mode - set project extent
    try:
        project.viewSettings().setDefaultViewExtent(extent)
        print(f"✓ Project extent set to: {lat:.6f}, {lon:.6f} (zoom: {zoom})")
    except Exception as e:
        print(f"⚠ Could not set extent: {e}")
        print(f"  Center manually to: {lat:.6f}, {lon:.6f}")

print("Map positioning complete!")
