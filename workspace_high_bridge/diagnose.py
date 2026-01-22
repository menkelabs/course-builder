"""Diagnose why the boundary isn't visible"""
from qgis.core import QgsProject
from qgis.utils import iface

project = QgsProject.instance()

print("=" * 50)
print("DIAGNOSTIC INFO")
print("=" * 50)

# Find the Course Boundary layer
bbox_layer = None
for layer in project.mapLayers().values():
    print(f"Layer: {layer.name()}")
    if "Course Boundary" in layer.name():
        bbox_layer = layer

if not bbox_layer:
    print("ERROR: Course Boundary layer not found!")
else:
    print(f"\nCourse Boundary layer found:")
    print(f"  Valid: {bbox_layer.isValid()}")
    print(f"  CRS: {bbox_layer.crs().authid()}")
    print(f"  Feature count: {bbox_layer.featureCount()}")
    print(f"  Extent: {bbox_layer.extent().toString()}")
    
    # Check visibility in layer tree
    root = project.layerTreeRoot()
    node = root.findLayer(bbox_layer.id())
    if node:
        print(f"  Visible in tree: {node.isVisible()}")
        print(f"  Layer index: {root.layerOrder().index(bbox_layer) if bbox_layer in root.layerOrder() else 'N/A'}")
    
    # Check renderer
    renderer = bbox_layer.renderer()
    if renderer:
        print(f"  Renderer type: {type(renderer).__name__}")
        symbol = renderer.symbol()
        if symbol:
            print(f"  Symbol type: {type(symbol).__name__}")
    
    # Check canvas extent vs layer extent
    canvas = iface.mapCanvas()
    canvas_extent = canvas.extent()
    layer_extent = bbox_layer.extent()
    
    print(f"\nCanvas extent: {canvas_extent.toString()}")
    print(f"Layer extent:  {layer_extent.toString()}")
    
    # Check if layer extent is within canvas extent
    if canvas_extent.contains(layer_extent):
        print("Layer is WITHIN canvas view")
    elif canvas_extent.intersects(layer_extent):
        print("Layer PARTIALLY visible in canvas")
    else:
        print("Layer is OUTSIDE canvas view - zooming now...")
        canvas.setExtent(layer_extent)
        canvas.refresh()
        print("Zoomed to layer extent")
    
    # Force layer to be visible
    if node:
        node.setItemVisibilityChecked(True)
    bbox_layer.triggerRepaint()
    canvas.refresh()
    print("\nForced visibility and refresh")

print("=" * 50)
