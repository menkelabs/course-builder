"""
Force Google Satellite tiles to load in QGIS
Run this in QGIS Python Console if map is blank
"""

from qgis.core import QgsProject, QgsCoordinateReferenceSystem, QgsRasterLayer
from qgis.utils import iface

print("=" * 60)
print("FORCING GOOGLE SATELLITE TILES TO LOAD")
print("=" * 60)

project = QgsProject.instance()

# 1. Ensure project CRS is EPSG:3857
project.setCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
print("✓ Project CRS set to EPSG:3857")

# 2. Find or create Google Satellite layer
google_layer = None
for layer in project.mapLayers().values():
    if "Google" in layer.name() and "Satellite" in layer.name():
        google_layer = layer
        break

if not google_layer:
    print("⚠ Google Satellite layer not found, creating new one...")
    # Create new Google Satellite layer
    google_uri = "type=xyz&url=https://mt1.google.com/vt?lyrs=s&x={x}&y={y}&z={z}&zmax=19&zmin=0"
    google_layer = QgsRasterLayer(google_uri, "Google Satellite", "wms")
    
    if google_layer.isValid():
        google_layer.setCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
        project.addMapLayer(google_layer)
        print("✓ Created and added Google Satellite layer")
    else:
        print("✗ Failed to create Google Satellite layer")
        print(f"  Error: {google_layer.error().message() if hasattr(google_layer, 'error') else 'Unknown'}")
        exit()

# 3. Ensure layer CRS matches project
google_layer.setCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
print(f"✓ Google Satellite CRS: {google_layer.crs().authid()}")

# 4. Make layer visible
root = project.layerTreeRoot()
layer_node = root.findLayer(google_layer.id())
if layer_node:
    layer_node.setItemVisibilityChecked(True)
    # Move to top
    try:
        parent = layer_node.parent()
        if parent:
            cloned = layer_node.clone()
            parent.insertChildNode(0, cloned)
            parent.removeChildNode(layer_node)
    except:
        pass
print("✓ Layer made visible and moved to top")

# 5. Force canvas to zoom to layer extent
if iface:
    canvas = iface.mapCanvas()
    
    # Get layer extent
    extent = google_layer.extent()
    print(f"  Layer extent: {extent.xMinimum():.2f}, {extent.yMinimum():.2f} to {extent.xMaximum():.2f}, {extent.yMaximum():.2f}")
    
    # If extent is invalid, set a default (Los Angeles area)
    if extent.width() < 1 or extent.height() < 1:
        print("  Layer extent is invalid, setting default extent (Los Angeles)...")
        from qgis.core import QgsRectangle, QgsPointXY, QgsCoordinateTransform
        source_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        dest_crs = QgsCoordinateReferenceSystem("EPSG:3857")
        transform = QgsCoordinateTransform(source_crs, dest_crs, project)
        
        # LA area in WGS84
        la_wgs84 = QgsRectangle(-118.5, 34.0, -118.3, 34.2)
        extent = transform.transformBoundingBox(la_wgs84)
    
    # Set canvas extent
    canvas.setExtent(extent)
    print(f"✓ Canvas extent set")
    
    # Force refresh
    google_layer.triggerRepaint()
    google_layer.reload()
    canvas.refresh()
    canvas.refreshAllLayers()
    
    # Small zoom to trigger tiles
    try:
        center = extent.center()
        canvas.zoomWithCenter(1.1, center)
        canvas.refresh()
        canvas.zoomWithCenter(0.9, center)
        canvas.refresh()
    except:
        pass
    
    print("✓ Canvas refreshed and zoomed")
    print("\n" + "=" * 60)
    print("CHECK THE MAP CANVAS NOW")
    print("=" * 60)
    print("\nIf still blank:")
    print("  1. Check Layers panel - ensure 'Google Satellite' is checked")
    print("  2. Right-click layer -> 'Refresh'")
    print("  3. Try: View -> Zoom Full")
    print("  4. Check internet connection")
    print("  5. Check firewall/proxy settings")
else:
    print("⚠ No iface available (not in GUI mode)")
