"""
QGIS Map Positioning Script
Run this in QGIS Python Console to position the map and show layers.
Or it will run automatically when QGIS opens (if added to startup).
"""

from qgis.core import QgsProject, QgsCoordinateReferenceSystem
from qgis.utils import iface

project = QgsProject.instance()

# CRITICAL: Ensure project CRS is EPSG:3857 for XYZ tiles
current_crs = project.crs()
if current_crs.authid() != "EPSG:3857":
    print(f"⚠ Project CRS is {current_crs.authid()}, changing to EPSG:3857...")
    project.setCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
    # Verify it was set
    verify_crs = project.crs()
    if verify_crs.authid() == "EPSG:3857":
        print("✓ Project CRS set to EPSG:3857")
    else:
        print(f"✗ Failed to set CRS, still {verify_crs.authid()}")
else:
    print(f"✓ Project CRS is correct: {current_crs.authid()}")

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
    # Ensure Google Satellite CRS matches project CRS
    layer_crs = google_layer.crs()
    if layer_crs.authid() != "EPSG:3857":
        print(f"⚠ Google layer CRS is {layer_crs.authid()}, fixing...")
        google_layer.setCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
        print("✓ Google Satellite CRS set to EPSG:3857")
    
    google_layer.setOpacity(1.0)
    google_layer.triggerRepaint()
    # Make sure it's in the layer tree and visible
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
    # Force reload tiles
    try:
        google_layer.reload()
    except:
        pass
    print("✓ Google Satellite layer made visible, CRS verified, and reloaded")
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
from qgis.core import QgsRectangle, QgsPointXY, QgsCoordinateReferenceSystem, QgsCoordinateTransform

# Convert WGS84 coordinates to Web Mercator (EPSG:3857) for extent
source_crs = QgsCoordinateReferenceSystem("EPSG:4326")  # WGS84
dest_crs = QgsCoordinateReferenceSystem("EPSG:3857")  # Web Mercator

# Create transform
transform = QgsCoordinateTransform(source_crs, dest_crs, project)

# Calculate appropriate scale based on zoom level FIRST (before extent)
# Zoom 15 ≈ 1:50,000, Zoom 16 ≈ 1:25,000, etc.
# Formula: scale = 156543.03392 / (2^zoom) (meters per pixel at equator)
meters_per_pixel = 156543.03392 / (2 ** 15)
# For zoom 15, this gives ~4.78 meters per pixel
# We want a reasonable view, so multiply by ~1000 pixels width = ~5000m scale
target_scale = meters_per_pixel * 1000

# Calculate extent in WGS84
zoom_factor = 0.01 / (2 ** (19 - 15))
buffer = zoom_factor * 5

wgs84_extent = QgsRectangle(
    -118.4144124,
    34.0908026,
    -118.40816240000001,
    34.0970526
)

# Transform to Web Mercator
extent = transform.transformBoundingBox(wgs84_extent)

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
        # Convert center point to Web Mercator for canvas
        center_wgs84 = QgsPointXY(-118.4112874, 34.0939276)
        center_mercator = transform.transform(center_wgs84)
        
        # Calculate appropriate scale based on zoom level
        # Zoom 15 ≈ 1:50,000, Zoom 16 ≈ 1:25,000, etc.
        # Formula: scale = 156543.03392 / (2^zoom) (meters per pixel at equator)
        meters_per_pixel = 156543.03392 / (2 ** 15)
        # For zoom 15, this gives ~4.78 meters per pixel
        # We want a reasonable view, so multiply by ~1000 pixels width = ~5000m scale
        target_scale = meters_per_pixel * 1000
        
        # Set center first
        canvas.setCenter(center_mercator)
        
        # Set scale (zoom level) - this fixes the "1:1" scale issue
        canvas.zoomScale(int(target_scale))
        
        # Trigger repaint and force tile loading on Google Satellite if it exists
        if google_layer:
            # Ensure layer is visible and at top of stack
            root = project.layerTreeRoot()
            layer_node = root.findLayer(google_layer.id())
            if layer_node:
                layer_node.setItemVisibilityChecked(True)
                # Move to top to ensure it renders first
                root.insertLayer(0, layer_node.clone())
                root.removeChildNode(layer_node)
            
            # Force tile loading by triggering multiple refresh methods
            google_layer.triggerRepaint()
            try:
                google_layer.reload()
            except:
                pass
            
            # Force canvas to request tiles
            try:
                canvas.setExtent(canvas.extent())  # Trigger extent change
            except:
                pass
        
        # Force multiple refreshes to trigger tile loading
        canvas.refresh()
        canvas.refreshAllLayers()
        
        # Small zoom in/out to force tile requests
        try:
            canvas.zoomWithCenter(1.01, center_mercator)
            canvas.refresh()
            canvas.zoomWithCenter(0.99, center_mercator)
            canvas.refresh()
        except:
            pass
        
        print(f"✓ Map positioned to: 34.093928, -118.411287 (zoom: 15, scale: 1:4777)")
        print("  If map is still blank:")
        print("  1. Try zooming in/out (mouse wheel) - this triggers tile loading")
        print("  2. Check Layers panel - ensure 'Google Satellite' checkbox is checked")
        print("  3. Right-click 'Google Satellite' layer -> 'Refresh'")
        print("  4. Check internet connection")
        print("  5. If still blank, manually add basemap:")
        print("     Browser -> XYZ Tiles -> New Connection")
        print("     URL: https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}")
    except Exception as e:
        # Fallback: use center point and zoom
        print(f"Using center point method (extent failed: {e})")
        try:
            # Convert to Web Mercator
            center_wgs84 = QgsPointXY(-118.4112874, 34.0939276)
            center_mercator = transform.transform(center_wgs84)
            
            canvas.setCenter(center_mercator)
            
            # Calculate scale from zoom level
            meters_per_pixel = 156543.03392 / (2 ** 15)
            target_scale = meters_per_pixel * 1000
            canvas.zoomScale(int(target_scale))
            
            canvas.refresh()
            if google_layer:
                google_layer.reload()
            print(f"✓ Map centered at: 34.093928, -118.411287 (zoom: 15, scale: 1:4777)")
        except Exception as e2:
            print(f"⚠ Could not position map: {e2}")
            print(f"  Manually navigate to: {lat:.6f}, {lon:.6f}")
            print(f"  Or use: View -> Zoom to Layer -> Google Satellite")
else:
    # Headless mode - set project extent
    try:
        project.viewSettings().setDefaultViewExtent(extent)
        print(f"✓ Project extent set to: {lat:.6f}, {lon:.6f} (zoom: {zoom})")
    except Exception as e:
        print(f"⚠ Could not set extent: {e}")
        print(f"  Center manually to: {lat:.6f}, {lon:.6f}")

print("Map positioning complete!")
