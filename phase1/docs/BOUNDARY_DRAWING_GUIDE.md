# Course Boundary Drawing Guide

Based on the OPCD LIDAR-to-Terrain process documentation.

## Boundary Size Guidelines

### For Most Courses (No Outer Plot Needed)

**Key Principle:** Include a **50-75 meter buffer** around the course perimeter.

**Steps:**
1. Draw the polygon around the golf course perimeter (fairways, rough, greens, etc.)
2. When you finish drawing, a pop-up window will appear showing the dimensions
3. **Round up** the dimensions to a multiple of 5 or 10 meters
4. **Add 100-150 meters** to each dimension
   - This creates a 50-75 meter buffer on each side (100-150m total = 50-75m per side)
5. Adjust your polygon if needed to match these dimensions

**Example:**
- If the course measures: 2000m x 1500m
- Round up to: 2000m x 1500m (already multiples of 10)
- Add buffer: 2100m x 1600m (add 100m to each)
- Final boundary should be approximately: **2100m x 1600m**

### When Outer Plot IS Needed

Only create an outer plot if you want to capture:
- Mountainous backgrounds
- Significant surrounding landscape features
- Extended terrain beyond the course

For most courses, the inner plot with buffer is sufficient.

## How to Draw the Boundary in QGIS

### Step 1: Prepare the Layer

1. Make sure **'Course Boundary'** layer is selected in the Layers panel
2. The layer should be visible and editable

### Step 2: Start Editing

1. Click the **'Toggle Editing'** button (pencil icon) in the toolbar
   - Or go to: **Layer → Toggle Editing**
   - The layer name will show an edit icon when editing is active

### Step 3: Draw the Polygon

1. Click the **'Add Polygon Feature'** tool (polygon icon)
   - Or press the **'A'** key (shortcut)
   - Or go to: **Edit → Add Polygon Feature**

2. **Draw the boundary:**
   - Click on the map to place each vertex (corner point) of the polygon
   - Follow the outer edge of the golf course:
     - Include all fairways
     - Include rough areas
     - Include greens and tees
     - Include a 50-75 meter buffer around the perimeter
   - Continue clicking to add more vertices
   - **Right-click** when finished to close the polygon

3. **When you right-click:**
   - A pop-up window will appear showing the polygon dimensions
   - **Note these dimensions** - you'll use them to calculate the buffer
   - Click **'OK'** to save the feature

### Step 4: Adjust for Buffer (if needed)

If the dimensions don't include the buffer yet:

1. Select the polygon (using the **Select Feature** tool)
2. Use **Vertex Tool** to adjust vertices and expand the boundary
3. Or delete and redraw with the buffer included

### Step 5: Save the Boundary

1. **Stop editing** by clicking **'Toggle Editing'** again (pencil icon)
   - QGIS will ask if you want to save changes - click **'Save'**

2. **Export as Shapefile:**
   - Right-click **'Course Boundary'** layer in Layers panel
   - Select **'Export' → 'Save Features As...'**
   - Choose **'ESRI Shapefile'** format
   - Save to: `workspace/Shapefiles/Course_Boundary.shp`
   - Click **'OK'** to save

3. The script will automatically detect the saved file and continue

## Tips

- **Zoom in/out** as needed while drawing (mouse wheel)
- **Pan the map** by holding middle mouse button or spacebar + drag
- **Undo** last vertex: Press **'U'** key
- **Delete feature**: Select it and press **Delete** key
- **Snap to features**: Enable snapping in Settings → Snapping Options
- **Measure distances**: Use the Measure Line tool to verify dimensions

## Keyboard Shortcuts

- **A** - Add Polygon Feature
- **U** - Undo last vertex
- **Delete** - Delete selected feature
- **Escape** - Cancel current drawing
- **Right-click** - Close polygon / Finish drawing

## Troubleshooting

**Polygon won't close:**
- Make sure you have at least 3 vertices
- Right-click when finished

**Can't see the layer:**
- Check that the layer checkbox is checked in Layers panel
- Zoom to layer: Right-click layer → Zoom to Layer

**Dimensions pop-up doesn't appear:**
- Make sure you right-clicked to finish the polygon
- Check that editing mode is active

**Can't save:**
- Make sure you stopped editing (Toggle Editing button)
- Check file permissions on the Shapefiles directory
