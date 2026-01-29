# Zoom Level Guide

Based on OPCD LIDAR-to-Terrain process documentation and best practices.

## Recommended Zoom Levels

### For Boundary Drawing (Initial View)

**Recommended: Zoom 15-16**

- **Zoom 15** (default): Shows full golf course with surrounding area
  - Scale: ~1:50,000
  - Resolution: ~4.78 meters per pixel
  - Good for: Seeing entire course, drawing boundary polygon
  - Coverage: Entire course + buffer visible

- **Zoom 16**: Closer view, individual holes visible
  - Scale: ~1:25,000
  - Resolution: ~2.39 meters per pixel
  - Good for: More detailed boundary drawing
  - Coverage: Course with less surrounding area

**Why 15-16?**
- Low enough to see the full course area
- High enough to see course features clearly
- Good balance between detail and coverage
- Prevents needing to pan around too much

### For Overlay Export (Max Zoom Setting)

**Recommended: Max Zoom 19** (per PDF Appendix D)

- **Default Max Zoom**: 20 (may not be available everywhere)
- **Recommended Max Zoom**: 19 (more reliable, per PDF)
- **If overlay is white**: Lower by 1 (try 18, then 17, etc.)

**How to Set:**
1. Right-click Bing/Google layer → Properties
2. Select "Source" tab
3. Change "Max zoom level" to 19
4. Click OK

**Why 19?**
- PDF states: "Normally setting the Max zoom level to 19 will create a valid overlay image"
- Zoom 20 may not be available in all areas
- If overlay exports as white, lower to 19 (or lower if needed)

## Zoom Level Reference

| Zoom | Scale | Meters/Pixel | Use Case |
|------|-------|--------------|----------|
| 10-12 | 1:500,000+ | 150+ m | Very wide view (entire region) |
| 13-14 | 1:100,000 | 20-40 m | Wide view (multiple courses) |
| **15** | **1:50,000** | **~4.78 m** | **RECOMMENDED: Full course view** |
| **16** | **1:25,000** | **~2.39 m** | **RECOMMENDED: Detailed course view** |
| 17-18 | 1:10,000 | 0.6-1.2 m | Close view (individual holes) |
| 19 | 1:5,000 | ~0.3 m | Very close (features visible) |
| 20 | 1:2,500 | ~0.15 m | Maximum detail (may not be available) |

## Configuration

### In Config File

```yaml
location:
  zoom_level: 15  # For initial map view and boundary drawing

gdal:
  overlay_max_zoom: 19  # Max zoom for overlay export (per PDF)
```

### Command Line

```bash
# Set initial zoom to 16 for closer view
python -m phase1.cli interactive-select \
  --course-name "My Course" \
  -o workspace/ \
  --zoom-level 16
```

## Tips

1. **Start with zoom 15** - See the full course area
2. **Zoom in to 16-17** if needed - For more precise boundary drawing
3. **Don't go too high** - Zoom 18+ may require too much panning
4. **For overlay export** - Always set max zoom to 19 (per PDF)
5. **If tiles don't load** - Try zooming in/out to trigger tile requests

## Troubleshooting

**Problem:** Map is blank or tiles don't load
- **Solution:** Zoom in/out (mouse wheel) to trigger tile loading
- **Solution:** Check layer max zoom setting (should be 19-20)

**Problem:** Overlay export is white
- **Solution:** Lower max zoom from 20 to 19 (per PDF Appendix D)
- **Solution:** If still white, try 18, then 17, etc.

**Problem:** Can't see full course
- **Solution:** Zoom out to 14-15
- **Solution:** Use "Zoom to Layer" on boundary layer
