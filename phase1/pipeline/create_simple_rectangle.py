"""
Simple script to create a visible rectangle - for testing.
This creates a rectangle with very obvious styling.
"""

from qgis.core import (
    QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY,
    QgsCoordinateReferenceSystem, QgsCoordinateTransform
)
from qgis.utils import iface

project = QgsProject.instance()

# Find boundary layer
boundary_layer = None
for layer in project.mapLayers().values():
    if "Course Boundary" in layer.name():
        boundary_layer = layer
        break

if not boundary_layer:
    print("✗ Course Boundary layer not found!")
    exit()

print("Found boundary layer, creating rectangle...")

# Get location from project or use High Bridge default
center_lat = float(project.readEntry("CourseBuilder", "center_lat", ["40.667975"])[0])
center_lon = float(project.readEntry("CourseBuilder", "center_lon", ["-74.893919"])[0])

# Create a 2000m square (in Web Mercator meters)
project_crs = project.crs()
source_crs = QgsCoordinateReferenceSystem("EPSG:4326")
transform = QgsCoordinateTransform(source_crs, project_crs, project)

center_wgs84 = QgsPointXY(center_lon, center_lat)
center_proj = transform.transform(center_wgs84)

# 2000m square = 1000m half-size
half_size = 1000.0
min_x = center_proj.x() - half_size
max_x = center_proj.x() + half_size
min_y = center_proj.y() - half_size
max_y = center_proj.y() + half_size

# Create rectangle
points = [
    QgsPointXY(min_x, min_y),
    QgsPointXY(max_x, min_y),
    QgsPointXY(max_x, max_y),
    QgsPointXY(min_x, max_y),
    QgsPointXY(min_x, min_y),
]

geom = QgsGeometry.fromPolygonXY([points])

# Start editing
if not boundary_layer.isEditable():
    boundary_layer.startEditing()

# Delete old features
boundary_layer.deleteFeatures([f.id() for f in boundary_layer.getFeatures()])

# Add new feature
feature = QgsFeature(boundary_layer.fields())
feature.setGeometry(geom)
boundary_layer.addFeature(feature)
boundary_layer.commitChanges()

print(f"✓ Rectangle created at {center_lat:.6f}, {center_lon:.6f}")
print(f"  Size: 2000m × 2000m")

# Force visibility
boundary_layer.setOpacity(1.0)
root = project.layerTreeRoot()
layer_node = root.findLayer(boundary_layer.id())
if layer_node:
    layer_node.setItemVisibilityChecked(True)

# Style with bright red outline
try:
    from qgis.core import QgsSimpleFillSymbolLayer, QgsSymbol, QgsSingleSymbolRenderer
    symbol = QgsSymbol.defaultSymbol(boundary_layer.geometryType())
    symbol_layer = QgsSimpleFillSymbolLayer.create({
        'color': '255,255,0,50',  # Yellow fill
        'outline_color': '255,0,0,255',  # Bright red outline
        'outline_width': '5',  # 5 pixel width - very visible!
        'outline_style': 'solid',
        'style': 'solid'
    })
    if symbol.symbolLayerCount() > 0:
        symbol.changeSymbolLayer(0, symbol_layer)
    renderer = QgsSingleSymbolRenderer(symbol)
    boundary_layer.setRenderer(renderer)
    print("  ✓ Applied bright red outline (5px width, yellow fill)")
except Exception as e:
    print(f"  ⚠ Styling error: {e}")
    print("  → Manually style: Right-click layer → Properties → Symbology")
    print("     Set outline to RED, width 5px")

# Zoom to it
if iface:
    canvas = iface.mapCanvas()
    extent = geom.boundingBox()
    extent.grow(extent.width() * 0.2)
    canvas.setExtent(extent)
    canvas.refresh()
    print("  ✓ Zoomed to rectangle")

boundary_layer.triggerRepaint()

print("\n✓ Done! You should see a bright red rectangle with yellow fill.")
print("  If not visible:")
print("  1. Right-click 'Course Boundary' → 'Zoom to Layer'")
print("  2. Check Layers panel - ensure checkbox is checked")
print("  3. Right-click → Properties → Symbology → Set outline to RED")
