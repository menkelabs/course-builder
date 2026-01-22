"""
Simple boundary creation - matches working example exactly.
Creates a NEW layer from scratch instead of using existing layer.
"""

from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsFeature,
    QgsGeometry,
    QgsRectangle,
    QgsFillSymbol,
    QgsSingleSymbolRenderer,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform
)
from qgis.utils import iface

project = QgsProject.instance()
project_crs = project.crs()

print("=" * 60)
print("CREATING BOUNDARY (Simple Method)")
print("=" * 60)
print(f"Project CRS: {project_crs.authid()}")

# Get location from project metadata
center_lat = float(project.readEntry("CourseBuilder", "center_lat", ["40.667975"])[0])
center_lon = float(project.readEntry("CourseBuilder", "center_lon", ["-74.893919"])[0])
size_meters = float(project.readEntry("CourseBuilder", "boundary_size", ["2000.0"])[0])

# Add buffer
buffer = 100.0
final_size = size_meters + buffer
final_size = round(final_size / 10.0) * 10.0

print(f"Center: {center_lat:.6f}, {center_lon:.6f}")
print(f"Size: {final_size}m × {final_size}m")

# Transform center from WGS84 to project CRS (EPSG:3857)
source_crs = QgsCoordinateReferenceSystem("EPSG:4326")
dest_crs = project_crs
transform = QgsCoordinateTransform(source_crs, dest_crs, project)

from qgis.core import QgsPointXY
center_wgs84 = QgsPointXY(center_lon, center_lat)
center_proj = transform.transform(center_wgs84)

# Calculate bounding box in PROJECT CRS (meters for EPSG:3857)
half_size = final_size / 2.0
xmin = center_proj.x() - half_size
ymin = center_proj.y() - half_size
xmax = center_proj.x() + half_size
ymax = center_proj.y() + half_size

print(f"Bounding box in {project_crs.authid()}:")
print(f"  X: {xmin:.2f} to {xmax:.2f}")
print(f"  Y: {ymin:.2f} to {ymax:.2f}")

# Remove existing boundary layer if it exists
existing_layer = None
for layer in project.mapLayers().values():
    if "Course Boundary" in layer.name() and isinstance(layer, QgsVectorLayer):
        existing_layer = layer
        break

if existing_layer:
    print(f"\nRemoving existing layer: {existing_layer.name()}")
    project.removeMapLayer(existing_layer.id())

# Create NEW layer from scratch (matches working example)
print(f"\nCreating new layer with CRS: {project_crs.authid()}")
bbox_layer = QgsVectorLayer(f"Polygon?crs={project_crs.authid()}", "Course Boundary", "memory")

if not bbox_layer.isValid():
    print("✗ Failed to create layer!")
    exit()

print("✓ Layer created")

# Get provider
prov = bbox_layer.dataProvider()

# Create rectangle geometry (matches working example exactly)
rect = QgsRectangle(xmin, ymin, xmax, ymax)
feat = QgsFeature()
feat.setGeometry(QgsGeometry.fromRect(rect))

# Add feature via provider (matches working example)
prov.addFeatures([feat])
bbox_layer.updateExtents()

print("✓ Feature added and extents updated")

# Style it (matches working example exactly)
symbol = QgsFillSymbol.createSimple({
    "color": "0,0,0,0",          # transparent fill
    "outline_color": "255,0,0,255",  # red outline
    "outline_width": "2"  # 2 pixel width (matches working example)
})
bbox_layer.setRenderer(QgsSingleSymbolRenderer(symbol))
print("✓ Styling applied")

# Add to project (normal add first)
project.addMapLayer(bbox_layer)
print("✓ Layer added to project")

# Force it to the very top of the layer tree (matches working example)
root = project.layerTreeRoot()
node = root.findLayer(bbox_layer.id())
if node:
    cloned = node.clone()
    parent = node.parent()
    if parent:
        parent.removeChildNode(node)
        root.insertChildNode(0, cloned)
        print("✓ Layer moved to top of layer tree")
    else:
        print("⚠ Could not find parent node")
else:
    print("⚠ Could not find layer node")

# Zoom to it (so you can actually see it)
bbox_layer.triggerRepaint()
try:
    if iface:
        iface.mapCanvas().setExtent(bbox_layer.extent())
        iface.mapCanvas().refresh()
        print("✓ Canvas refreshed and zoomed to layer extent")
except NameError:
    print("⚠ iface not found (not running inside QGIS GUI). Layer still created.")

print("\n" + "=" * 60)
print("✓ BOUNDARY CREATED SUCCESSFULLY")
print(f"  Feature count: {bbox_layer.featureCount()}")
print(f"  Layer extent: {bbox_layer.extent().toString()}")
print("=" * 60)
