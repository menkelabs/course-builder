"""
Auto-generated boundary creation script.
Coordinates for: 40.6679753, -74.8939186
Run this in QGIS Python Console to create the boundary polygon.
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

# Input coordinates (WGS84)
center_lat = 40.6679753
center_lon = -74.8939186
half_size = 1050  # meters

project = QgsProject.instance()
project_crs = project.crs()
print("Project CRS:", project_crs.authid())

# Transform center from WGS84 to project CRS
wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
transform = QgsCoordinateTransform(wgs84, project_crs, project)
center_wgs84 = QgsPointXY(center_lon, center_lat)
center_proj = transform.transform(center_wgs84)

print(f"Center in WGS84: {center_lat}, {center_lon}")
print(f"Center in {project_crs.authid()}: {center_proj.x():.2f}, {center_proj.y():.2f}")

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
    # Activate the Vertex Tool automatically
    iface.actionVertexTool().trigger()
except NameError:
    print("iface not found. Layer still created.")

print("=" * 50)
print("Boundary created successfully!")
print(f"Center: 40.6679753, -74.8939186")
print(f"Size: {half_size * 2}m x {half_size * 2}m (includes buffer)")
print(f"Extent: {bbox_layer.extent().toString()}")
print("=" * 50)
print("You can now adjust the boundary vertices to match the course.")
