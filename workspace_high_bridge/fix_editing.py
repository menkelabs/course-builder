"""Fix vertex handle size and remove yellow highlight"""
from qgis.core import QgsProject, QgsSettings, QgsFillSymbol, QgsSingleSymbolRenderer
from qgis.utils import iface

project = QgsProject.instance()

# Make vertex markers bigger
settings = QgsSettings()
settings.setValue("/qgis/digitizing/marker_size_mm", 4.0)  # Default is usually 2.0
settings.setValue("/qgis/digitizing/marker_size", 4)
print("✓ Increased vertex marker size to 4mm")

# Find Course Boundary layer
bbox_layer = None
for layer in project.mapLayers().values():
    if "Course Boundary" in layer.name():
        bbox_layer = layer
        break

if bbox_layer:
    # Clear selection (removes yellow highlight)
    bbox_layer.removeSelection()
    print("✓ Cleared selection (removed yellow highlight)")
    
    # Re-apply red outline style (transparent fill)
    symbol = QgsFillSymbol.createSimple({
        "color": "0,0,0,0",          # transparent fill
        "outline_color": "255,0,0,255",  # red outline
        "outline_width": "2"
    })
    bbox_layer.setRenderer(QgsSingleSymbolRenderer(symbol))
    bbox_layer.triggerRepaint()
    print("✓ Re-applied red outline style (transparent fill)")
    
    # Make it the active layer and enable editing
    iface.setActiveLayer(bbox_layer)
    if not bbox_layer.isEditable():
        bbox_layer.startEditing()
    print("✓ Editing enabled")
    
    # Refresh canvas
    iface.mapCanvas().refresh()
    
    print("")
    print("=" * 50)
    print("VERTEX HANDLES SHOULD NOW BE BIGGER")
    print("1. Press 'V' for Vertex Tool")
    print("2. Zoom in on a corner")
    print("3. Click on the vertex marker (circle) and drag")
    print("=" * 50)
else:
    print("ERROR: Course Boundary layer not found!")
