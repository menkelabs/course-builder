"""
Diagnostic script to check if boundary polygon exists and is visible.
Run this in QGIS Python Console to troubleshoot boundary visibility.
"""

from qgis.core import QgsProject
from qgis.utils import iface

project = QgsProject.instance()

print("=" * 60)
print("BOUNDARY LAYER DIAGNOSTICS")
print("=" * 60)

# Find boundary layer
boundary_layer = None
for layer in project.mapLayers().values():
    if "Course Boundary" in layer.name() and hasattr(layer, 'featureCount'):
        boundary_layer = layer
        break

if not boundary_layer:
    print("✗ Course Boundary layer NOT FOUND")
    print("\nAvailable layers:")
    for layer in project.mapLayers().values():
        print(f"  - {layer.name()} ({type(layer).__name__})")
else:
    print(f"✓ Found layer: {boundary_layer.name()}")
    print(f"  Layer ID: {boundary_layer.id()}")
    print(f"  CRS: {boundary_layer.crs().authid()}")
    print(f"  Feature count: {boundary_layer.featureCount()}")
    
    if boundary_layer.featureCount() == 0:
        print("\n⚠ PROBLEM: Layer has NO features!")
        print("  The polygon was not created.")
        print("  Try running create_square_boundary.py again.")
    else:
        print(f"\n✓ Layer has {boundary_layer.featureCount()} feature(s)")
        
        # Check layer visibility
        root = project.layerTreeRoot()
        layer_node = root.findLayer(boundary_layer.id())
        if layer_node:
            is_visible = layer_node.isVisible()
            print(f"  Visible in tree: {is_visible}")
            if not is_visible:
                print("  → FIX: Check the checkbox in Layers panel")
        else:
            print("  ⚠ Layer node not found in tree")
        
        # Get feature extent
        features = list(boundary_layer.getFeatures())
        if features:
            feature = features[0]
            geom = feature.geometry()
            if geom and not geom.isEmpty():
                extent = geom.boundingBox()
                print(f"\n  Feature extent:")
                print(f"    X: {extent.xMinimum():.2f} to {extent.xMaximum():.2f}")
                print(f"    Y: {extent.yMinimum():.2f} to {extent.yMaximum():.2f}")
                print(f"    Width: {extent.width():.2f}")
                print(f"    Height: {extent.height():.2f}")
                
                # Check if extent is reasonable
                if extent.width() < 0.001 or extent.height() < 0.001:
                    print("\n  ⚠ PROBLEM: Extent is too small!")
                    print("    The polygon might be in wrong CRS or location")
                elif extent.width() > 1000000 or extent.height() > 1000000:
                    print("\n  ⚠ PROBLEM: Extent is too large!")
                    print("    The polygon might be in wrong CRS")
                else:
                    print("\n  ✓ Extent looks reasonable")
                    
                    # Try to zoom to it
                    if iface:
                        canvas = iface.mapCanvas()
                        canvas.setExtent(extent)
                        canvas.refresh()
                        print("  ✓ Zoomed to feature extent")
            else:
                print("\n  ⚠ PROBLEM: Feature has no geometry!")
        else:
            print("\n  ⚠ No features found in layer")
        
        # Check renderer/symbol
        renderer = boundary_layer.renderer()
        if renderer:
            symbol = renderer.symbol()
            if symbol:
                print(f"\n  Symbol type: {type(symbol).__name__}")
                print(f"  Symbol layers: {symbol.symbolLayerCount()}")
            else:
                print("\n  ⚠ No symbol on renderer")
        else:
            print("\n  ⚠ No renderer on layer")

print("\n" + "=" * 60)
print("If you still don't see the rectangle:")
print("1. Right-click 'Course Boundary' → Properties → Symbology")
print("2. Set outline color to RED, width to 3 pixels")
print("3. Set fill to transparent or light color")
print("4. Click OK")
print("5. Right-click 'Course Boundary' → 'Zoom to Layer'")
print("=" * 60)
