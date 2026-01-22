"""
Fix the Course Boundary layer CRS to match the project CRS (EPSG:3857).
Run this in QGIS Python Console if the boundary layer has wrong CRS.
"""

from qgis.core import QgsProject, QgsVectorLayer, QgsCoordinateReferenceSystem, QgsCoordinateTransform

project = QgsProject.instance()
project_crs = project.crs()

print("=" * 60)
print("FIXING BOUNDARY LAYER CRS")
print("=" * 60)
print(f"Project CRS: {project_crs.authid()}")

# Find boundary layer
boundary_layer = None
for layer in project.mapLayers().values():
    if "Course Boundary" in layer.name() and isinstance(layer, QgsVectorLayer):
        boundary_layer = layer
        break

if not boundary_layer:
    print("✗ Course Boundary layer not found!")
    exit()

print(f"Found layer: {boundary_layer.name()}")
print(f"Current layer CRS: {boundary_layer.crs().authid()}")

# Check if CRS matches
if boundary_layer.crs().authid() == project_crs.authid():
    print("✓ CRS already matches project CRS")
else:
    print(f"⚠ CRS mismatch detected!")
    print(f"  Fixing layer CRS to match project: {project_crs.authid()}")
    
    # If layer has features, we need to transform them
    feature_count = boundary_layer.featureCount()
    if feature_count > 0:
        print(f"  Layer has {feature_count} feature(s) - transforming geometry...")
        
        # Get transform
        source_crs = boundary_layer.crs()
        dest_crs = project_crs
        transform = QgsCoordinateTransform(source_crs, dest_crs, project)
        
        # Start editing
        if not boundary_layer.isEditable():
            boundary_layer.startEditing()
        
        # Transform all features
        features_to_update = []
        for feature in boundary_layer.getFeatures():
            geom = feature.geometry()
            if geom and not geom.isEmpty():
                geom.transform(transform)
                feature.setGeometry(geom)
                features_to_update.append(feature)
        
        # Update features
        boundary_layer.dataProvider().changeGeometryValues({
            f.id(): f.geometry() for f in features_to_update
        })
        
        boundary_layer.commitChanges()
        print("  ✓ Features transformed to new CRS")
    
    # Set layer CRS
    boundary_layer.setCrs(project_crs)
    print(f"  ✓ Layer CRS set to {project_crs.authid()}")

# Verify
final_crs = boundary_layer.crs()
if final_crs.authid() == project_crs.authid():
    print("\n✓ SUCCESS: Boundary layer CRS now matches project CRS")
    print(f"  Layer CRS: {final_crs.authid()}")
    print(f"  Project CRS: {project_crs.authid()}")
    
    # Refresh
    boundary_layer.triggerRepaint()
    
    # Zoom to layer if it has features
    if boundary_layer.featureCount() > 0:
        from qgis.utils import iface
        if iface:
            iface.mapCanvas().setExtent(boundary_layer.extent())
            iface.mapCanvas().refresh()
            print("  ✓ Zoomed to layer extent")
else:
    print(f"\n✗ FAILED: CRS still doesn't match")
    print(f"  Layer: {final_crs.authid()}, Project: {project_crs.authid()}")

print("=" * 60)
