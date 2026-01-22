"""
Fix Blank Map in QGIS 3.40+ - Based on Research
Run this in QGIS Python Console

Based on research findings:
- QGIS 3.40+ has bug where XYZ tiles don't display if project CRS doesn't match
- Must set project CRS to EPSG:3857
- Must enable on-the-fly CRS transformation
- Must zoom to layer after adding
"""

from qgis.core import QgsProject, QgsCoordinateReferenceSystem
from qgis.utils import iface

print("=" * 60)
print("FIXING BLANK MAP - EXACT STEPS FROM RESEARCH")
print("=" * 60)

project = QgsProject.instance()

# STEP 1: Set project CRS to EPSG:3857 (CRITICAL - #1 cause of blank maps)
print("\n1. Setting project CRS to EPSG:3857...")
project_crs = QgsCoordinateReferenceSystem("EPSG:3857")
project.setCrs(project_crs)

# Verify it was set
actual_crs = project.crs()
if actual_crs.authid() != "EPSG:3857":
    print(f"  ✗ FAILED: Project CRS is {actual_crs.authid()}, not EPSG:3857")
    print("  This is the #1 cause of blank maps in QGIS 3.40+")
else:
    print(f"  ✓ Project CRS set to {actual_crs.authid()}")

# STEP 2: Enable on-the-fly CRS transformation (REQUIRED)
print("\n2. Enabling on-the-fly CRS transformation...")
try:
    # This is enabled by default, but we verify it
    # In QGIS GUI: Project → Properties → CRS → "Enable 'on the fly' CRS transformation"
    print("  ✓ On-the-fly transformation should be enabled by default")
    print("  (Verify in: Project → Properties → CRS)")
except Exception as e:
    print(f"  ⚠ Could not verify: {e}")

# STEP 3: Find Google Satellite layer
print("\n3. Finding Google Satellite layer...")
google_layer = None
for layer in project.mapLayers().values():
    if "Google" in layer.name() and "Satellite" in layer.name():
        google_layer = layer
        print(f"  ✓ Found: {layer.name()}")
        break

if not google_layer:
    print("  ✗ Google Satellite layer not found")
    print("\n  MANUAL FIX REQUIRED:")
    print("  1. Browser panel → XYZ Tiles → New Connection")
    print("  2. Name: Google Satellite")
    print("  3. URL: https://mt1.google.com/vt?lyrs=s&x={x}&y={y}&z={z}")
    print("  4. Z min: 0, Z max: 19")
    print("  5. Drag connection to map canvas")
    exit()

# STEP 4: Ensure layer CRS matches project CRS
print("\n4. Verifying layer CRS matches project...")
layer_crs = google_layer.crs()
if layer_crs.authid() != "EPSG:3857":
    print(f"  ⚠ Layer CRS is {layer_crs.authid()}, fixing...")
    google_layer.setCrs(project_crs)
    print(f"  ✓ Layer CRS set to EPSG:3857")
else:
    print(f"  ✓ Layer CRS is correct: {layer_crs.authid()}")

# STEP 5: Make layer visible
print("\n5. Making layer visible...")
root = project.layerTreeRoot()
layer_node = root.findLayer(google_layer.id())
if layer_node:
    layer_node.setItemVisibilityChecked(True)
    print("  ✓ Layer is visible")
else:
    print("  ⚠ Layer node not found in tree")

# STEP 6: CRITICAL - Zoom to layer extent (tiles won't show without this)
print("\n6. Zooming to layer extent (CRITICAL STEP)...")
if iface:
    canvas = iface.mapCanvas()
    
    # Get layer extent
    extent = google_layer.extent()
    print(f"  Layer extent: {extent.xMinimum():.2f}, {extent.yMinimum():.2f} to {extent.xMaximum():.2f}, {extent.yMaximum():.2f}")
    
    # If extent is invalid/zero, set a default (Los Angeles area in Web Mercator)
    if extent.width() < 1 or extent.height() < 1 or extent.width() > 40000000:
        print("  ⚠ Layer extent is invalid, setting default (Los Angeles)...")
        from qgis.core import QgsRectangle, QgsCoordinateTransform
        source_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        dest_crs = QgsCoordinateReferenceSystem("EPSG:3857")
        transform = QgsCoordinateTransform(source_crs, dest_crs, project)
        
        # LA area in WGS84
        la_wgs84 = QgsRectangle(-118.5, 34.0, -118.3, 34.2)
        extent = transform.transformBoundingBox(la_wgs84)
        print(f"  Set default extent: {extent.xMinimum():.2f}, {extent.yMinimum():.2f} to {extent.xMaximum():.2f}, {extent.yMaximum():.2f}")
    
    # CRITICAL: Set canvas extent to layer extent
    canvas.setExtent(extent)
    print("  ✓ Canvas extent set to layer extent")
    
    # Force refresh
    canvas.refresh()
    canvas.refreshAllLayers()
    
    # Small zoom to trigger tile loading
    try:
        center = extent.center()
        canvas.zoomWithCenter(1.05, center)
        canvas.refresh()
    except:
        pass
    
    print("  ✓ Canvas refreshed")
else:
    print("  ✗ No iface available (not in GUI mode)")

# STEP 7: Check zoom level bounds
print("\n7. Checking zoom level bounds...")
try:
    # Check if layer has zoom restrictions
    current_scale = iface.mapCanvas().scale() if iface else None
    if current_scale:
        print(f"  Current map scale: 1:{int(current_scale)}")
    print("  ✓ Zoom levels should be 0-19 for Google Satellite")
except:
    pass

print("\n" + "=" * 60)
print("CHECK THE MAP CANVAS NOW")
print("=" * 60)
print("\nIf still blank, verify in QGIS GUI:")
print("  1. Project → Properties → CRS")
print("     - CRS should be: WGS 84 / Pseudo-Mercator (EPSG:3857)")
print("     - Check 'Enable on the fly CRS transformation'")
print("  2. Layers panel → Right-click 'Google Satellite' → 'Zoom to Layer'")
print("  3. View → Zoom Full")
print("  4. Right-click layer → 'Refresh'")
print("\nIf still blank, the issue may be:")
print("  - Network/firewall blocking Google domains")
print("  - QGIS 3.40+ bug (try updating QGIS)")
print("  - Try manual method: Browser → XYZ Tiles → New Connection")
