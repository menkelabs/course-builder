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

# Find Bing Aerial layer
bing_layer = None
for layer in project.mapLayers().values():
    if "Bing" in layer.name() and "Aerial" in layer.name():
        bing_layer = layer
        break

if not bing_layer:
    print("⚠ Bing Aerial layer not found, creating new one...")
    from qgis.core import QgsRasterLayer
    # Bing uses quadkey format - need double braces in f-string
    bing_uri = "type=xyz&url=https://ecn.t3.tiles.virtualearth.net/tiles/a{q}.jpeg?g=1"
    bing_layer = QgsRasterLayer(bing_uri, "Bing Aerial", "wms")
    
    if not bing_layer.isValid():
        error_msg = bing_layer.error().message() if hasattr(bing_layer, 'error') and bing_layer.error() else 'Unknown error'
        print(f"✗ Bing layer failed to load: {error_msg}")
    else:
        bing_layer.setCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
        project.addMapLayer(bing_layer)
        print("✓ Created and added Bing Aerial layer")

if bing_layer:
    # Ensure Bing Aerial CRS matches project CRS
    layer_crs = bing_layer.crs()
    if layer_crs.authid() != "EPSG:3857":
        print(f"⚠ Bing layer CRS is {layer_crs.authid()}, fixing...")
        bing_layer.setCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
        print("✓ Bing Aerial CRS set to EPSG:3857")
    
    bing_layer.setOpacity(1.0)
    bing_layer.triggerRepaint()
    # Make sure it's in the layer tree and visible
    root = project.layerTreeRoot()
    layer_node = root.findLayer(bing_layer.id())
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
        bing_layer.reload()
    except:
        pass
    print("✓ Bing Aerial layer made visible, CRS verified, and reloaded")
else:
    print("⚠ Bing Aerial layer not found and could not be created")
    print("  You may need to add it manually:")
    print("  Browser panel -> XYZ Tiles -> New Connection")
    print("  URL: https://ecn.t3.tiles.virtualearth.net/tiles/a{q}.jpeg?g=1")

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
    -74.29639929999999,
    40.10188,
    -74.2901493,
    40.108129999999996
)

# Transform to Web Mercator
extent = transform.transformBoundingBox(wgs84_extent)

# Find Bing Aerial layer
bing_layer = None
for layer in project.mapLayers().values():
    if "Bing" in layer.name() and "Aerial" in layer.name():
        bing_layer = layer
        break

# Set canvas extent if iface is available (GUI mode)
if iface:
    canvas = iface.mapCanvas()
    try:
        # Convert center point to Web Mercator for canvas
        center_wgs84 = QgsPointXY(-74.2932743, 40.105005)
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
        
        # Trigger repaint and force tile loading on Bing Aerial if it exists
        if bing_layer:
            # Ensure layer is visible and at top of stack
            root = project.layerTreeRoot()
            layer_node = root.findLayer(bing_layer.id())
            if layer_node:
                layer_node.setItemVisibilityChecked(True)
                # Move to top to ensure it renders first
                try:
                    parent = layer_node.parent()
                    if parent:
                        cloned = layer_node.clone()
                        parent.insertChildNode(0, cloned)
                        parent.removeChildNode(layer_node)
                except:
                    pass
            
            # Force tile loading by triggering multiple refresh methods
            bing_layer.triggerRepaint()
            try:
                bing_layer.reload()
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
        
        print(f"✓ Map positioned to: {lat:.6f}, {lon:.6f} (zoom: {zoom}, scale: 1:{target_scale_value})")
        print("  If map is still blank:")
        print("  1. Try zooming in/out (mouse wheel) - this triggers tile loading")
        print("  2. Check Layers panel - ensure 'Bing Aerial' checkbox is checked")
        print("  3. Right-click 'Bing Aerial' layer -> 'Refresh'")
        print("  4. Check internet connection")
        print("  5. If still blank, manually add basemap:")
        print("     Browser -> XYZ Tiles -> New Connection")
        print("     URL: https://ecn.t3.tiles.virtualearth.net/tiles/a{q}.jpeg?g=1")
    except Exception as e:
        # Fallback: use center point and zoom
        print(f"Using center point method (extent failed: {e})")
        try:
            # Convert to Web Mercator
            center_wgs84 = QgsPointXY(-74.2932743, 40.105005)
            center_mercator = transform.transform(center_wgs84)
            
            canvas.setCenter(center_mercator)
            
            # Calculate scale from zoom level
            meters_per_pixel = 156543.03392 / (2 ** 15)
            target_scale = meters_per_pixel * 1000
            canvas.zoomScale(int(target_scale))
            
            canvas.refresh()
            if bing_layer:
                bing_layer.reload()
            print(f"✓ Map centered at: {lat:.6f}, {lon:.6f} (zoom: {zoom}, scale: 1:{target_scale_value})")
        except Exception as e2:
            print(f"⚠ Could not position map: {e2}")
            print(f"  Manually navigate to: {lat:.6f}, {lon:.6f}")
            print(f"  Or use: View -> Zoom to Layer -> Bing Aerial")
else:
    # Headless mode - set project extent
    try:
        project.viewSettings().setDefaultViewExtent(extent)
        print(f"✓ Project extent set to: {lat:.6f}, {lon:.6f} (zoom: {zoom})")
    except Exception as e:
        print(f"⚠ Could not set extent: {e}")
        print(f"  Center manually to: {lat:.6f}, {lon:.6f}")

print("Map positioning complete!")
