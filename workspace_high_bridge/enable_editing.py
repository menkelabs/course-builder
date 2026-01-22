"""Enable editing on Course Boundary layer and select the feature"""
from qgis.core import QgsProject
from qgis.utils import iface

project = QgsProject.instance()

# Find Course Boundary layer
bbox_layer = None
for layer in project.mapLayers().values():
    if "Course Boundary" in layer.name():
        bbox_layer = layer
        break

if not bbox_layer:
    print("ERROR: Course Boundary layer not found!")
else:
    # Make it the active layer
    iface.setActiveLayer(bbox_layer)
    print(f"✓ Set active layer: {bbox_layer.name()}")
    
    # Start editing if not already
    if not bbox_layer.isEditable():
        bbox_layer.startEditing()
        print("✓ Editing enabled")
    else:
        print("✓ Editing already enabled")
    
    # Select all features in the layer
    bbox_layer.selectAll()
    feature_count = bbox_layer.selectedFeatureCount()
    print(f"✓ Selected {feature_count} feature(s)")
    
    # Zoom to selection
    if feature_count > 0:
        iface.mapCanvas().zoomToSelected(bbox_layer)
        print("✓ Zoomed to selection")
    
    print("")
    print("=" * 50)
    print("NOW YOU CAN:")
    print("1. Press 'V' for Vertex Tool - drag corners to resize")
    print("2. Or go to Edit menu → Move Feature(s) - drag entire box")
    print("=" * 50)
