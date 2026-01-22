"""Remove yellow fill and set transparent"""
from qgis.core import QgsProject, QgsFillSymbol, QgsSingleSymbolRenderer
from qgis.utils import iface
from qgis.PyQt.QtGui import QColor

project = QgsProject.instance()

# Find Course Boundary layer
bbox_layer = None
for layer in project.mapLayers().values():
    if "Course Boundary" in layer.name():
        bbox_layer = layer
        break

if bbox_layer:
    # Clear any selection
    bbox_layer.removeSelection()
    
    # Create symbol with completely transparent fill
    symbol = QgsFillSymbol.createSimple({
        "color": "255,255,255,0",      # completely transparent
        "outline_color": "255,0,0",    # red
        "outline_width": "2",
        "outline_style": "solid"
    })
    
    # Make sure fill is transparent
    symbol.setColor(QColor(0, 0, 0, 0))  # RGBA with 0 alpha = transparent
    
    # Apply renderer
    renderer = QgsSingleSymbolRenderer(symbol)
    bbox_layer.setRenderer(renderer)
    
    # Refresh
    bbox_layer.triggerRepaint()
    iface.mapCanvas().refresh()
    
    print("✓ Applied transparent fill with red outline")
    print("The box should now have NO fill color, just a red border")
else:
    print("ERROR: Course Boundary layer not found!")
