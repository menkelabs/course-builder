# Manual Google Satellite Setup in QGIS

If the automated setup isn't working and you see a blank map, follow these steps:

## Method 1: Add via Browser Panel (Recommended)

1. **Open Browser Panel** (if not visible: View → Panels → Browser Panel)

2. **Expand "XYZ Tiles"** in the Browser panel

3. **Right-click "XYZ Tiles"** → **"New Connection..."**

4. **Fill in the dialog:**
   - **Name:** `Google Satellite`
   - **URL:** `https://mt1.google.com/vt?lyrs=s&x={x}&y={y}&z={z}`
   - **Z min:** `0`
   - **Z max:** `19`
   - **Authentication:** Leave blank

5. **Click OK**

6. **Drag the new "Google Satellite" connection** from Browser panel to the map canvas (or double-click it)

7. **The map should now show Google Satellite imagery**

## Method 2: Test with OpenStreetMap First

To verify QGIS can load tiles at all:

1. **Browser → XYZ Tiles → New Connection**
2. **Name:** `OpenStreetMap`
3. **URL:** `https://tile.openstreetmap.org/{z}/{x}/{y}.png`
4. **Click OK, then drag to canvas**

If OpenStreetMap works but Google doesn't, it might be:
- Firewall blocking Google domains
- Google rate limiting
- Network/proxy issues

## Troubleshooting

### Still blank after adding manually?

1. **Check Project CRS:**
   - Project → Properties → CRS
   - Should be "WGS 84 / Pseudo-Mercator" (EPSG:3857)
   - If not, select it and click OK

2. **Check Layer Visibility:**
   - Layers panel → Ensure "Google Satellite" checkbox is checked
   - Right-click layer → "Zoom to Layer"

3. **Refresh Layer:**
   - Right-click "Google Satellite" → "Refresh"

4. **Check Internet:**
   - Try opening `https://mt1.google.com/vt?lyrs=s&x=1&y=1&z=1` in a web browser
   - Should show a small map tile image

5. **Check QGIS Console for Errors:**
   - View → Panels → Log Messages
   - Look for red error messages about tile loading

## Alternative: Use Different Tile Service

If Google Satellite doesn't work, try:

- **ESRI World Imagery:** `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}`
- **Mapbox Satellite:** Requires API key
- **Bing Aerial:** Requires API key
