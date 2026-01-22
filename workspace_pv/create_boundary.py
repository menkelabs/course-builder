"""
Auto-generated boundary creation script.
Default coordinates: 40.105005, -74.2932743
Run this in QGIS Python Console to create the boundary polygon.

The boundary will be created at the CURRENT MAP CENTER - 
zoom/pan to position the map first, then run this script!
"""

from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsFeature,
    QgsGeometry,
    QgsRectangle,
    QgsPointXY,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFillSymbol,
    QgsSingleSymbolRenderer
)

half_size = 1050  # meters (2100m total = 2000m + 100m buffer)

project = QgsProject.instance()
project_crs = project.crs()
print("Project CRS:", project_crs.authid())

# Get the CURRENT map canvas center (where user has zoomed/panned to)
canvas = iface.mapCanvas()
center_proj = canvas.center()

print(f"Creating boundary at CURRENT MAP CENTER:")
print(f"  Center in {project_crs.authid()}: {center_proj.x():.2f}, {center_proj.y():.2f}")

# Convert to WGS84 for display
wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
transform_to_wgs84 = QgsCoordinateTransform(project_crs, wgs84, project)
center_wgs84 = transform_to_wgs84.transform(center_proj)
print(f"  Center in WGS84: {center_wgs84.y():.6f}, {center_wgs84.x():.6f}")

# Calculate bounding box in project CRS
xmin = center_proj.x() - half_size
xmax = center_proj.x() + half_size
ymin = center_proj.y() - half_size
ymax = center_proj.y() + half_size

print(f"BBox: {xmin:.2f}, {ymin:.2f} to {xmax:.2f}, {ymax:.2f}")

# Remove existing Course Boundary layer if it exists
for layer in list(project.mapLayers().values()):
    if "Course Boundary" in layer.name():
        print(f"Removing existing layer: {layer.name()}")
        project.removeMapLayer(layer.id())

# Create memory layer with project CRS
bbox_layer = QgsVectorLayer(f"Polygon?crs={project_crs.authid()}", "Course Boundary", "memory")
if not bbox_layer.isValid():
    raise RuntimeError("Failed to create memory layer")

prov = bbox_layer.dataProvider()

# Create rectangle and add feature
rect = QgsRectangle(xmin, ymin, xmax, ymax)
feat = QgsFeature()
feat.setGeometry(QgsGeometry.fromRect(rect))
prov.addFeatures([feat])
bbox_layer.updateExtents()

# Style: TRANSPARENT fill, red outline
from qgis.PyQt.QtGui import QColor
symbol = QgsFillSymbol.createSimple({
    "color": "255,255,255,0",
    "outline_color": "255,0,0",
    "outline_width": "2",
    "outline_style": "solid"
})
symbol.setColor(QColor(0, 0, 0, 0))  # Force transparent
bbox_layer.setRenderer(QgsSingleSymbolRenderer(symbol))

# Add to project (addMapLayer with True adds to legend)
project.addMapLayer(bbox_layer, True)

# Ensure layer is visible
root = project.layerTreeRoot()
node = root.findLayer(bbox_layer.id())
if node:
    node.setItemVisibilityChecked(True)
    print(f"Layer node found and set visible")

# Make vertex markers bigger for easier editing
from qgis.core import QgsSettings
settings = QgsSettings()
settings.setValue("/qgis/digitizing/marker_size_mm", 5.0)
settings.setValue("/qgis/digitizing/marker_size", 5)

# Set as active layer and enable editing
iface.setActiveLayer(bbox_layer)
bbox_layer.startEditing()

# Zoom to boundary
try:
    iface.mapCanvas().setExtent(bbox_layer.extent())
    iface.mapCanvas().refresh()
    
    # Show Advanced Digitizing Toolbar and activate Move Feature tool
    try:
        adv_toolbar = iface.advancedDigitizeToolBar()
        if adv_toolbar:
            adv_toolbar.show()
    except:
        pass
    
    # Enable wheel zoom for map navigation independent of the box
    canvas = iface.mapCanvas()
    canvas.setWheelFactor(2.0)  # Standard zoom factor
    canvas.enableAntiAliasing(True)
    
    # Activate Move Feature tool (for moving the entire polygon)
    try:
        iface.actionMoveFeature().trigger()
    except:
        # Fallback to vertex tool if move feature not available
        iface.actionVertexTool().trigger()
except NameError:
    print("iface not found. Layer still created.")

print("=" * 50)
print("Boundary created at current map center!")
print(f"Size: {half_size * 2}m x {half_size * 2}m (includes buffer)")
print(f"Extent: {bbox_layer.extent().toString()}")
print("=" * 50)
print("")
print("NEXT STEPS:")
print("  1. DRAG the box to reposition it over the course")
print("  2. Press V for Vertex Tool to resize/reshape corners")
print("  3. Use MOUSE WHEEL to zoom in/out for detail")
print("  4. Use MIDDLE MOUSE or SPACE+DRAG to pan")
print("")
print("When done, save the boundary layer as a shapefile.")
