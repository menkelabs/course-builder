# qgis-plan.md

OPCD-aligned MCP plan (QGIS + GDAL only) to automate terrain prep for GSPro using the OPCD Stage 2–5 DEM/DTM workflow.

## Architecture
- MCP server exposes OPCD-named tools and validates inputs/paths.
- One QGIS worker (PyQGIS or `qgis_process`) plus GDAL CLI.
- Every run writes `Runs/<timestamp>/run.json` and `Runs/<timestamp>/trace.jsonl`.

## Workspace layout (OPCD-style)
- `DEM/` input DEM/DTM tiles
- `Shapefiles/Inner.*`, `Shapefiles/Outer.*`
- `TIF/<Course>_merged.tif`
- `Heightmap/INNER/<Course>_Lidar_Surface_Inner.tif` and `.raw`
- `Heightmap/OUTER/<Course>_Lidar_Surface_Outer.tif` and `.raw`
- `Overlays/` (Google/Bing TIFs and 8192 JPGs)

## Embabel nested tool support (Matryoshka-style)
Model the workflow as nested tools:
- `opcd.pipeline.run_all_qgis`
  - `opcd.stage2.setup_project`
  - `opcd.stage3.merge_dem_tiles`
  - `opcd.stage4.make_heightmaps_and_overlays`
  - `opcd.stage5.convert_for_unity`
  - `opcd.stageX.validate`

Each stage tool calls step-level tools and records outputs into a shared `context.json` so runs are resumable.

## MCP tool surface (QGIS-only)
Stage 2:
- `opcd.project.init(courseName, workspacePath, templateQgz)`
- `opcd.crs.detect_and_set(samplePath, mode, partialFilterText?, metadataCrsText?)`
- `opcd.plots.create_inner_outer(innerSize, outerSize, origin?)`

Stage 3 (DEM):
- `opcd.qgis.merge_dem_tiles(demPaths[], outMergedTif)`

Stage 4:
- `opcd.qgis.assign_crs_to_tif(tifPath, epsg)`
- `opcd.qgis.clip_heightmap_outer(mergedTif, outerShp, outFloat32Tif)`
- `opcd.qgis.clip_heightmap_inner(mergedOrOuterTif, innerShp, outFloat32Tif)`
- `opcd.qgis.get_raster_minmax(heightmapTif, outMinMaxJson, updateMinMaxXlsx)`
- `opcd.qgis.export_overlays(innerHeightmapTif, outerHeightmapTif, providers=[google,bing], outSize=16000)`

Stage 5:
- `opcd.gdal.heightmap_tif_to_raw(inputFloat32Tif, min, max, outRaw, outSize=4097)`
- `opcd.gdal.overlay_tif_to_jpg(overlayTifs[], outSize=8192, quality=95)`

## Validation (post-run)
- Required files exist in the expected folders.
- CRS consistency across merged DEM, heightmaps, and plots.
- RAW dimensions are 4097x4097.
- Overlay JPG dimensions are 8192x8192 and not blank.

## Execution
Preferred: call one tool
- `opcd.pipeline.run_all_qgis`

Or stepwise:
- Stage 2 tools
- Stage 3 merge
- Stage 4 clip + overlays
- Stage 5 conversions
- Validation
