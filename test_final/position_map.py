"""
QGIS Map Positioning Script
Run this in QGIS Python Console to position the map and show layers.
Or it will run automatically when QGIS opens (if added to startup).
"""

from qgis.core import QgsProject
from qgis.utils import iface

project = QgsProject.instance()

# Remove duplicate Google Satellite layers and ensure one is visible
all_google = []
for layer in project.mapLayers().values():
    if layer.name() == "Google Satellite":
        all_google.append(layer)

# Remove duplicates, keep first
if len(all_google) > 1:
    print(f"⚠ Found {len(all_google)} Google Satellite layers, removing duplicates...")
    for dup in all_google[1:]:
        project.removeMapLayer(dup.id())
        print(f"  Removed: {dup.id()}")
    google_layer = all_google[0]
elif len(all_google) == 1:
    google_layer = all_google[0]
else:
    google_layer = None

if google_layer:
    google_layer.setOpacity(1.0)
    google_layer.triggerRepaint()
    # Make sure it's in the layer tree and visible
    root = project.layerTreeRoot()
    layer_node = root.findLayer(google_layer.id())
    if layer_node:
        layer_node.setItemVisibilityChecked(True)
    # Force reload tiles
    try:
        google_layer.reload()
    except:
        pass
    print("✓ Google Satellite layer made visible and reloaded")
else:
    print("⚠ Google Satellite layer not found")
    print("  You may need to add it manually:")
    print("  Browser panel -> XYZ Tiles -> New Connection")
    print("  URL: https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}")

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
    -118.4144124,
    34.0908026,
    -118.40816240000001,
    34.0970526
)

# Remove any duplicate Google Satellite layers first
all_google_layers = []
for layer in project.mapLayers().values():
    if layer.name() == "Google Satellite":
        all_google_layers.append(layer)

# Keep only the first one, remove duplicates
if len(all_google_layers) > 1:
    print(f"⚠ Found {len(all_google_layers)} Google Satellite layers, removing duplicates...")
    for dup_layer in all_google_layers[1:]:
        project.removeMapLayer(dup_layer.id())
        print(f"  Removed duplicate: {dup_layer.id()}")
    google_layer = all_google_layers[0]
elif len(all_google_layers) == 1:
    google_layer = all_google_layers[0]
else:
    google_layer = None

# Set canvas extent if iface is available (GUI mode)
if iface:
    canvas = iface.mapCanvas()
    try:
        # Set extent first
        canvas.setExtent(extent)
        
        # Trigger repaint on Google Satellite if it exists (before refresh)
        if google_layer:
            google_layer.triggerRepaint()
            try:
                google_layer.reload()
            except:
                pass
        
        # Force refresh of canvas
        canvas.refresh()
        
        # Zoom slightly to trigger tile loading
        canvas.zoomWithCenter(1.1, QgsPointXY(-118.4112874, 34.0939276))
        canvas.refresh()
        
        print(f"✓ Map positioned to: {lat:.6f}, {lon:.6f} (zoom: {zoom})")
        print("  If map is still blank:")
        print("  1. Try zooming in/out (mouse wheel)")
        print("  2. Check Layers panel - ensure 'Google Satellite' is checked")
        print("  3. Right-click layer -> 'Refresh'")
        print("  4. Check internet connection")
    except Exception as e:
        # Fallback: use center point and zoom
        print(f"Using center point method (extent failed: {e})")
        try:
            canvas.setCenter(QgsPointXY(-118.4112874, 34.0939276))
            # Approximate zoom based on zoom level
            # Zoom level 15 ≈ scale 1:50000, level 16 ≈ 1:25000, etc.
            scale = 50000 / (2 ** (15 - 15))
            canvas.zoomScale(int(scale))
            canvas.refresh()
            if google_layer:
                google_layer.reload()
            print(f"✓ Map centered at: {lat:.6f}, {lon:.6f} (zoom: {zoom})")
        except Exception as e2:
            print(f"⚠ Could not position map: {e2}")
            print(f"  Manually navigate to: {lat:.6f}, {lon:.6f}")
else:
    # Headless mode - set project extent
    try:
        project.viewSettings().setDefaultViewExtent(extent)
        print(f"✓ Project extent set to: {lat:.6f}, {lon:.6f} (zoom: {zoom})")
    except Exception as e:
        print(f"⚠ Could not set extent: {e}")
        print(f"  Center manually to: {lat:.6f}, {lon:.6f}")

print("Map positioning complete!")
