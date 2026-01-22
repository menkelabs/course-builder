# Research Findings: PyQGIS Polygon Visibility Issues

## Sources Found:
1. QGIS Official Documentation (docs.qgis.org)
2. GIS StackExchange (multiple threads)
3. PyQGIS Developer Cookbook

## Key Findings:

### 1. **CRITICAL: Must call `updateExtents()` after adding features**
- Source: QGIS PyQGIS Developer Cookbook
- Issue: Without this, QGIS doesn't know the layer's spatial extent and won't render it
- Fix: Added `boundary_layer.updateExtents()` after `commitChanges()`

### 2. **Layer must be added to project explicitly**
- Source: Multiple StackExchange threads
- Issue: Memory layers won't show unless added with `QgsProject.instance().addMapLayer(layer)`
- Status: Already done in template creation

### 3. **CRS Mismatch is the #1 cause of invisible polygons**
- Source: Reddit QGIS community, StackExchange
- Issue: If coordinates are in degrees (EPSG:4326) but layer/project is in meters (EPSG:3857), polygon will be tiny/invisible
- Our issue: Diagnostic showed layer CRS is EPSG:4326 but project is EPSG:3857
- Fix: Template now creates layer with EPSG:3857, and removes/recreates if wrong CRS detected

### 4. **Proper styling method for polygons**
- Source: QGIS Documentation, StackExchange
- Method: `QgsFillSymbol.createSimple()` with `QgsSingleSymbolRenderer`
- Old method: Using `QgsSimpleFillSymbolLayer.create()` - this may not work reliably
- Fix: Changed to `QgsFillSymbol.createSimple({'color': 'yellow', 'outline_color': 'red', ...})`

### 5. **Must refresh canvas after changes**
- Source: PyQGIS Cookbook
- Methods: `layer.triggerRepaint()` AND `canvas.refresh()`
- Fix: Added both calls

## What Was Actually Changed:

1. **qgis_template.py**:
   - Line 194: Changed `Polygon?crs={crs}` to `Polygon?crs=EPSG:3857` (hardcoded to match project)
   - Lines 219-226: Added logic to remove and recreate layer if CRS is wrong

2. **create_square_boundary.py**:
   - Line 162: Added `boundary_layer.updateExtents()` after commit
   - Lines 181-192: Changed styling to use `QgsFillSymbol.createSimple()`
   - Line 212: Added `boundary_layer.triggerRepaint()`
   - Line 230: Added `canvas.refresh()`
   - Lines 172-178: Added extent validation

## The Real Problem:

The diagnostic showed:
- Layer CRS: EPSG:4326 (WRONG)
- Project CRS: EPSG:3857 (CORRECT)
- Feature count: 0

This means either:
1. The template wasn't regenerated with the fix, OR
2. The existing layer in the project file has the wrong CRS and needs to be fixed

## Next Steps:

The template fix will only work if:
1. Delete the old `.qgz` file
2. Regenerate the template (which will create layer with EPSG:3857)
3. OR run the fix_boundary_crs.py script in QGIS to fix existing layer
