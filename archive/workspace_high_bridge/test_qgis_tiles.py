"""
Test script to verify QGIS can load XYZ tile layers.
Run this in QGIS Python Console to diagnose tile loading issues.
"""

from qgis.core import QgsProject, QgsRasterLayer, QgsCoordinateReferenceSystem
from qgis.utils import iface

print("=" * 60)
print("QGIS Tile Loading Diagnostic Test")
print("=" * 60)

project = QgsProject.instance()

# Test 1: OpenStreetMap (most reliable, no API key needed)
print("\n1. Testing OpenStreetMap XYZ tiles...")
osm_uri = "type=xyz&url=https://tile.openstreetmap.org/{z}/{x}/{y}.png&zmax=19&zmin=0"
osm_layer = QgsRasterLayer(osm_uri, "OpenStreetMap Test", "wms")

if osm_layer.isValid():
    print("   ✓ OpenStreetMap layer is VALID")
    osm_layer.setCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
    project.addMapLayer(osm_layer)
    
    # Try to zoom to layer
    if iface:
        canvas = iface.mapCanvas()
        canvas.setExtent(osm_layer.extent())
        canvas.refresh()
        print("   ✓ Added and zoomed to OpenStreetMap")
        print("   → Check map canvas - do you see OpenStreetMap tiles?")
else:
    print("   ✗ OpenStreetMap layer is INVALID")
    if hasattr(osm_layer, 'error'):
        err = osm_layer.error()
        if err:
            print(f"   Error: {err.message()}")
else:
    print("   ✗ Failed to create OpenStreetMap layer")

# Test 2: Google Satellite
print("\n2. Testing Google Satellite XYZ tiles...")
google_uri = "type=xyz&url=https://mt1.google.com/vt?lyrs=s&x={x}&y={y}&z={z}&zmax=19&zmin=0"
google_layer = QgsRasterLayer(google_uri, "Google Satellite Test", "wms")

if google_layer.isValid():
    print("   ✓ Google Satellite layer is VALID")
    google_layer.setCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
    project.addMapLayer(google_layer)
    
    if iface:
        canvas = iface.mapCanvas()
        # Zoom to a known location (Los Angeles)
        from qgis.core import QgsRectangle, QgsPointXY, QgsCoordinateTransform, QgsCoordinateReferenceSystem
        source_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        dest_crs = QgsCoordinateReferenceSystem("EPSG:3857")
        transform = QgsCoordinateTransform(source_crs, dest_crs, project)
        
        # LA area
        la_wgs84 = QgsRectangle(-118.5, 34.0, -118.3, 34.2)
        la_mercator = transform.transformBoundingBox(la_wgs84)
        canvas.setExtent(la_mercator)
        canvas.refresh()
        print("   ✓ Added and zoomed to Los Angeles area")
        print("   → Check map canvas - do you see Google Satellite tiles?")
else:
    print("   ✗ Google Satellite layer is INVALID")
    if hasattr(google_layer, 'error'):
        err = google_layer.error()
        if err:
            print(f"   Error: {err.message()}")

# Test 3: Check project CRS
print("\n3. Checking project CRS...")
project_crs = project.crs()
print(f"   Project CRS: {project_crs.authid()}")
if project_crs.authid() != "EPSG:3857":
    print("   ⚠ Warning: Project CRS is not EPSG:3857 (Web Mercator)")
    print("   XYZ tiles work best with EPSG:3857")
    print("   Consider: project.setCrs(QgsCoordinateReferenceSystem('EPSG:3857'))")
else:
    print("   ✓ Project CRS is correct (EPSG:3857)")

# Test 4: Check canvas extent
if iface:
    print("\n4. Checking map canvas...")
    canvas = iface.mapCanvas()
    extent = canvas.extent()
    print(f"   Canvas extent: {extent.xMinimum():.2f}, {extent.yMinimum():.2f} to {extent.xMaximum():.2f}, {extent.yMaximum():.2f}")
    print(f"   Canvas width: {extent.width():.2f}")
    print(f"   Canvas height: {extent.height():.2f}")
    
    if extent.width() < 1 or extent.height() < 1:
        print("   ⚠ Warning: Canvas extent is very small - tiles may not load")
        print("   Try: View -> Zoom Full or View -> Zoom to Layer")

# Test 5: List all layers
print("\n5. Current layers in project:")
layers = project.mapLayers()
if layers:
    for layer_id, layer in layers.items():
        print(f"   - {layer.name()} ({layer.type()}) - Valid: {layer.isValid()}")
        if hasattr(layer, 'crs'):
            print(f"     CRS: {layer.crs().authid()}")
else:
    print("   No layers in project")

print("\n" + "=" * 60)
print("Diagnostic complete!")
print("=" * 60)
print("\nIf you see tiles:")
print("  → QGIS tile loading works! The issue is with how we're creating the template.")
print("\nIf you DON'T see tiles:")
print("  → Check network connection")
print("  → Check firewall settings")
print("  → Try manually: Browser panel -> XYZ Tiles -> New Connection")
print("  → URL: https://tile.openstreetmap.org/{z}/{x}/{y}.png")
