# Zoom and Boundary Explained

## How Zooming Works with Tile Services

**Yes, zooming automatically requests different tiles:**

### Zoom Levels and Tile Resolution

- **Zoom Out (lower number, e.g., zoom 10):**
  - Fewer tiles needed to cover the same area
  - Lower resolution (less detail)
  - Each tile covers a larger geographic area
  - Example: Zoom 10 might show entire state

- **Zoom In (higher number, e.g., zoom 18):**
  - More tiles needed to cover the same area
  - Higher resolution (more detail)
  - Each tile covers a smaller geographic area
  - Example: Zoom 18 shows individual buildings

### How QGIS Requests Tiles

When you zoom in/out in QGIS:
1. QGIS calculates which tiles are visible in the current view
2. It automatically requests those tiles from Bing/Google servers
3. Higher zoom = more tiles requested (more detail)
4. Lower zoom = fewer tiles requested (less detail)

**Example:**
- Zoom 15: Might need ~16 tiles to cover a golf course
- Zoom 18: Might need ~256 tiles to cover the same course (16x more tiles!)

### Tile Service Behavior

Bing Aerial and Google Satellite are **XYZ tile services**:
- They serve pre-rendered image tiles at different zoom levels
- Each zoom level has a fixed resolution
- QGIS automatically requests the appropriate zoom level based on your view
- You don't manually control which tiles are downloaded - QGIS does it automatically

## The Square Boundary - What It Does

**Yes, the square is just for SELECTION!**

### What the Boundary Defines

The square boundary polygon you draw in QGIS defines:

1. **Geographic Area to Process:**
   - What area of the Earth to download LIDAR/DEM data for
   - What area to clip from the merged DEM tiles
   - What area to create the heightmap from

2. **Selection Area Only:**
   - The boundary is a **selection tool**
   - It tells the pipeline: "Process THIS area"
   - It doesn't affect tile resolution or zoom level

### How It Works in the Pipeline

```
1. You draw square boundary in QGIS (e.g., 2000m × 2000m)
   ↓
2. Pipeline extracts geographic bounds from boundary
   ↓
3. Pipeline downloads LIDAR/DEM data for that area
   ↓
4. Pipeline clips DEM to the boundary shape
   ↓
5. Pipeline resamples to create heightmap (4097×4097 pixels)
   ↓
6. Final heightmap is ALWAYS square (4097×4097) regardless of geographic dimensions
```

### Why Square?

- **Unity requires square heightmaps:** 4097×4097 pixels
- **Square boundary in meters** helps maintain proper aspect ratio
- If boundary is rectangular (e.g., 2000m × 1500m), the heightmap will be stretched/squished
- Square boundary (e.g., 2000m × 2000m) = square heightmap = correct aspect ratio

### Important Notes

1. **Zoom level doesn't affect the boundary:**
   - You can zoom in/out to see more/less detail while drawing
   - The boundary size in **meters** is what matters, not zoom level
   - Zoom is just for visualization

2. **Boundary size in meters ≠ heightmap pixels:**
   - Boundary: 2000m × 2000m (geographic area)
   - Heightmap: 4097×4097 pixels (always fixed)
   - The pipeline resamples the geographic area to fit 4097×4097 pixels

3. **Tile resolution is independent:**
   - Tiles are for **viewing** the map in QGIS
   - LIDAR/DEM data is downloaded separately (not from tiles)
   - The boundary selects which LIDAR/DEM data to use

## Summary

- **Zooming:** Automatically requests more/fewer tiles based on zoom level (for viewing only)
- **Square Boundary:** Defines the geographic area to process (selection tool)
- **Final Heightmap:** Always 4097×4097 pixels (resampled from selected area)
- **Square boundary in meters** ensures correct aspect ratio in final heightmap
