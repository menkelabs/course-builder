"""
Automatically create a square boundary polygon in QGIS.

This script creates a square polygon centered on the initial location,
which the user can then adjust to match the actual course boundaries.

Based on OPCD guidelines:
- Square dimensions (for 4097x4097 heightmap)
- 50-75 meter buffer included
- Dimensions rounded to multiples of 5 or 10 meters
"""

from qgis.core import (
    QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY,
    QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsRectangle
)
from qgis.utils import iface


def create_square_boundary(
    center_lat: float,
    center_lon: float,
    size_meters: float = 2000.0,
    layer_name: str = "Course Boundary"
) -> bool:
    """
    Create a square boundary polygon centered on the given coordinates.
    
    Args:
        center_lat: Center latitude (WGS84)
        center_lon: Center longitude (WGS84)
        size_meters: Size of square in meters (default: 2000m)
        layer_name: Name of the boundary layer
    
    Returns:
        True if successful, False otherwise
    """
    project = QgsProject.instance()
    
    # Find boundary layer
    boundary_layer = None
    for layer in project.mapLayers().values():
        if layer.name() == layer_name and isinstance(layer, QgsVectorLayer):
            boundary_layer = layer
            break
    
    if not boundary_layer:
        print(f"✗ Boundary layer '{layer_name}' not found")
        print("  Make sure the QGIS template was created correctly")
        return False
    
    # CRITICAL: Verify and fix CRS if needed
    layer_crs = boundary_layer.crs()
    if layer_crs.authid() != project_crs.authid():
        print(f"⚠ CRS mismatch detected!")
        print(f"  Layer CRS: {layer_crs.authid()}")
        print(f"  Project CRS: {project_crs.authid()}")
        print(f"  Fixing layer CRS to match project...")
        boundary_layer.setCrs(project_crs)
        # Verify fix
        if boundary_layer.crs().authid() != project_crs.authid():
            print(f"  ✗ Failed to fix CRS!")
            return False
        print(f"  ✓ Layer CRS fixed to {project_crs.authid()}")
    
    # Get project CRS
    project_crs = project.crs()
    source_crs = QgsCoordinateReferenceSystem("EPSG:4326")  # WGS84
    dest_crs = project_crs
    
    # Create coordinate transform
    transform = QgsCoordinateTransform(source_crs, dest_crs, project)
    
    # Convert center to project CRS
    center_wgs84 = QgsPointXY(center_lon, center_lat)
    center_proj = transform.transform(center_wgs84)
    
    # Calculate half-size in meters
    # For Web Mercator (EPSG:3857), 1 degree ≈ 111,320 meters at equator
    # But we need to account for latitude
    if dest_crs.authid() == "EPSG:3857":
        # Web Mercator: meters are approximately constant
        half_size = size_meters / 2.0
        # Create square in Web Mercator
        min_x = center_proj.x() - half_size
        max_x = center_proj.x() + half_size
        min_y = center_proj.y() - half_size
        max_y = center_proj.y() + half_size
    else:
        # For geographic CRS, convert meters to degrees
        # Approximate: 1 degree ≈ 111,320 meters
        meters_per_degree = 111320.0
        half_size_deg = (size_meters / 2.0) / meters_per_degree
        min_x = center_proj.x() - half_size_deg
        max_x = center_proj.x() + half_size_deg
        min_y = center_proj.y() - half_size_deg
        max_y = center_proj.y() + half_size_deg
    
    # Create rectangle geometry directly (simpler and more reliable)
    from qgis.core import QgsRectangle
    rect = QgsRectangle(min_x, min_y, max_x, max_y)
    square_geom = QgsGeometry.fromRect(rect)
    
    print(f"  ✓ Rectangle created: {min_x:.2f}, {min_y:.2f} to {max_x:.2f}, {max_y:.2f}")
    print(f"  ✓ Size: {rect.width():.2f}m × {rect.height():.2f}m")
    
    # Ensure layer CRS matches project CRS
    if boundary_layer.crs().authid() != project_crs.authid():
        print(f"  ⚠ CRS mismatch: layer={boundary_layer.crs().authid()}, project={project_crs.authid()}")
        print(f"  → Setting layer CRS to match project")
        boundary_layer.setCrs(project_crs)
    
    # Delete existing features (if any) using provider
    existing_ids = [f.id() for f in boundary_layer.getFeatures()]
    if existing_ids:
        boundary_layer.dataProvider().deleteFeatures(existing_ids)
        print(f"  ✓ Deleted {len(existing_ids)} existing feature(s)")
    
    # Create feature and add directly via provider (simpler, more reliable)
    feature = QgsFeature()
    feature.setGeometry(square_geom)
    
    # Add feature using provider (matches working example)
    prov = boundary_layer.dataProvider()
    success = prov.addFeatures([feature])
    
    if not success:
        print(f"  ✗ Failed to add feature")
        return False
    
    print(f"  ✓ Feature added")
    
    # CRITICAL: Update extents (required for QGIS to know where the layer is)
    boundary_layer.updateExtents()
    print(f"  ✓ Layer extents updated")
    
    # Verify feature was saved
    feature_count = boundary_layer.featureCount()
    print(f"  ✓ Layer now has {feature_count} feature(s)")
    if feature_count == 0:
        print("  ⚠ WARNING: Feature count is 0 after commit!")
        return False
    
    # Verify extent is valid
    layer_extent = boundary_layer.extent()
    if not layer_extent.isValid() or layer_extent.width() == 0 or layer_extent.height() == 0:
        print(f"  ⚠ WARNING: Layer extent is invalid or zero!")
        print(f"    Extent: {layer_extent.toString()}")
    else:
        print(f"  ✓ Layer extent is valid: {layer_extent.width():.2f}m × {layer_extent.height():.2f}m")
    
    # Style the layer (matches working example exactly)
    try:
        from qgis.core import QgsFillSymbol, QgsSingleSymbolRenderer
        # Create fill symbol with transparent fill and red outline (matches working example)
        symbol = QgsFillSymbol.createSimple({
            "color": "0,0,0,0",          # transparent fill
            "outline_color": "255,0,0,255",  # red outline
            "outline_width": "1.2"        # outline width
        })
        # Apply renderer
        boundary_layer.setRenderer(QgsSingleSymbolRenderer(symbol))
        print("  ✓ Applied red outline styling (transparent fill, red outline)")
    except Exception as e:
        print(f"  ⚠ Could not apply styling: {e}")
        import traceback
        traceback.print_exc()
        print("  (Layer should still be visible - check Layers panel)")
    
    # Ensure layer is visible and on top (matches working example)
    boundary_layer.setOpacity(1.0)
    root = project.layerTreeRoot()
    layer_node = root.findLayer(boundary_layer.id())
    if layer_node:
        layer_node.setItemVisibilityChecked(True)
        # Move to top of layer stack (matches working example)
        try:
            parent = layer_node.parent()
            if parent:
                cloned = layer_node.clone()
                parent.insertChildNode(0, cloned)
                parent.removeChildNode(layer_node)
                print("  ✓ Layer moved to top of layer stack")
        except:
            pass
        print("  ✓ Layer is visible in layer tree")
    else:
        print("  ⚠ Layer node not found - check Layers panel manually")
    
    # Trigger repaint
    boundary_layer.triggerRepaint()
    print("  ✓ Triggered layer repaint")
    
    # Zoom to layer extent
    if iface:
        canvas = iface.mapCanvas()
        layer_extent = boundary_layer.extent()
        if layer_extent.isValid() and layer_extent.width() > 0 and layer_extent.height() > 0:
            # Add a small buffer
            layer_extent.grow(layer_extent.width() * 0.1)
            canvas.setExtent(layer_extent)
            canvas.refresh()
            print("  ✓ Zoomed to boundary extent and refreshed canvas")
        else:
            print("  ⚠ Layer extent is invalid")
        
        print(f"\n✓ Boundary created successfully!")
        print(f"  Feature count: {boundary_layer.featureCount()}")
        print(f"  Layer extent: {boundary_layer.extent().toString()}")
    else:
        print("  ⚠ iface not available - run this in QGIS Python Console")
    
    print(f"✓ Created square boundary: {size_meters}m × {size_meters}m")
    print(f"  Center: {center_lat:.6f}, {center_lon:.6f}")
    print(f"  You can now adjust the vertices to match the course boundaries")
    
    return True


# Main execution
if __name__ == "__main__" or True:
    # Get initial location from project metadata or use defaults
    project = QgsProject.instance()
    
    # Try to get location from project metadata
    center_lat = float(project.readEntry("CourseBuilder", "center_lat", ["40.667975"])[0])
    center_lon = float(project.readEntry("CourseBuilder", "center_lon", ["-74.893919"])[0])
    size_meters = float(project.readEntry("CourseBuilder", "boundary_size", ["2000.0"])[0])
    
    # Round size to multiple of 10 meters
    size_meters = round(size_meters / 10.0) * 10.0
    
    # Add 100-150m buffer (50-75m per side) as per OPCD guidelines
    # Default: add 100m (50m buffer per side)
    buffer = 100.0
    final_size = size_meters + buffer
    
    # Round to multiple of 10
    final_size = round(final_size / 10.0) * 10.0
    
    print("Creating square boundary polygon...")
    print(f"  Center: {center_lat:.6f}, {center_lon:.6f}")
    print(f"  Size: {final_size}m × {final_size}m (includes {buffer/2}m buffer per side)")
    
    success = create_square_boundary(center_lat, center_lon, final_size)
    
    if success:
        print("\n✓ Square boundary created successfully!")
        print("  You can now:")
        print("  1. Select the polygon (Select Feature tool)")
        print("  2. Use Vertex Tool to adjust vertices to match course boundaries")
        print("  3. Save when done (Toggle Editing → Save)")
    else:
        print("\n✗ Failed to create boundary. Check QGIS console for errors.")
