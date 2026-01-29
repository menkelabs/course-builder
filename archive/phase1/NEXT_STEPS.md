# Phase 1 - Next Steps

## Plan Viability Assessment

✅ **The plan is viable!** All operations described in `qgis-plan.md` are standard GIS operations that QGIS and GDAL can handle:

- **Stage 2 (Project Setup)**: QGIS project initialization, CRS detection, shapefile creation
- **Stage 3 (DEM Merging)**: Standard raster merge operation
- **Stage 4 (Heightmaps)**: Raster clipping, CRS assignment, overlay generation
- **Stage 5 (Unity Conversion)**: GDAL format conversion (TIF→RAW, TIF→JPG)

**Key Technical Considerations:**
- Use `qgis_process` CLI for QGIS operations (included with QGIS, no GUI needed)
- Use GDAL Python bindings (rasterio, geopandas) for GDAL operations
- All file formats and operations are well-documented and standard

---

## Implementation Roadmap

### Phase 1.1: Core Infrastructure (Week 1)

#### 1.1.1 QGIS Process Wrapper
- [ ] Create `pipeline/qgis_process.py` module
  - [ ] Implement `QGISProcess` class to wrap `qgis_process` CLI
  - [ ] Add methods: `run_algorithm()`, `list_algorithms()`, `check_available()`
  - [ ] Handle QGIS process path detection (auto-detect or config)
  - [ ] Add error handling and logging
  - [ ] Write tests for QGIS process wrapper

#### 1.1.2 GDAL Operations Module
- [ ] Create `pipeline/gdal_ops.py` module
  - [ ] Implement `GDALOperations` class
  - [ ] Add methods: `tif_to_raw()`, `tif_to_jpg()`, `get_raster_info()`
  - [ ] Use rasterio for TIF operations
  - [ ] Use GDAL CLI tools via subprocess for format conversions
  - [ ] Write tests for GDAL operations

#### 1.1.3 Workspace Management
- [ ] Create `pipeline/workspace.py` module
  - [ ] Implement `WorkspaceManager` class
  - [ ] Add methods: `create_structure()`, `validate_structure()`, `get_paths()`
  - [ ] Ensure directory creation follows OPCD layout
  - [ ] Write tests for workspace management

#### 1.1.4 Run Tracking
- [ ] Create `pipeline/tracking.py` module
  - [ ] Implement `RunTracker` class
  - [ ] Add methods: `start_run()`, `log_step()`, `save_context()`, `load_context()`
  - [ ] Write `run.json` and `trace.jsonl` files
  - [ ] Support resumable runs via `context.json`
  - [ ] Write tests for run tracking

---

### Phase 1.2: Stage 2 - Project Setup (Week 2)

#### 1.2.1 Project Initialization
- [ ] Create `pipeline/stage2_project.py` module
  - [ ] Implement `ProjectSetup` class
  - [ ] Add method: `init_project(course_name, workspace_path, template_qgz)`
  - [ ] Create QGIS project file (.qgz) if template provided
  - [ ] Set up workspace directory structure
  - [ ] Write tests

#### 1.2.2 CRS Detection
- [ ] Add method: `detect_and_set_crs(sample_path, mode, ...)`
  - [ ] Detect CRS from DEM files using rasterio
  - [ ] Support manual CRS override
  - [ ] Validate CRS consistency across inputs
  - [ ] Write tests for CRS detection

#### 1.2.3 Plot Creation
- [ ] Add method: `create_inner_outer_plots(inner_size, outer_size, origin)`
  - [ ] Generate inner and outer boundary shapefiles
  - [ ] Use shapely/geopandas for geometry creation
  - [ ] Save to `Shapefiles/Inner.*` and `Shapefiles/Outer.*`
  - [ ] Write tests for plot creation

---

### Phase 1.3: Stage 3 - DEM Merging (Week 2-3)

#### 1.3.1 DEM Tile Merging
- [ ] Create `pipeline/stage3_dem.py` module
  - [ ] Implement `DEMMerger` class
  - [ ] Add method: `merge_dem_tiles(dem_paths, output_path)`
  - [ ] Use QGIS `gdal:merge` algorithm via qgis_process
  - [ ] Handle CRS transformations if needed
  - [ ] Validate merged output
  - [ ] Write tests with sample DEM tiles

---

### Phase 1.4: Stage 4 - Heightmaps and Overlays (Week 3-4)

#### 1.4.1 Heightmap Clipping
- [ ] Create `pipeline/stage4_heightmaps.py` module
  - [ ] Implement `HeightmapGenerator` class
  - [ ] Add method: `clip_heightmap_outer(merged_tif, outer_shp, output)`
  - [ ] Add method: `clip_heightmap_inner(merged_tif, inner_shp, output)`
  - [ ] Use QGIS `gdal:cliprasterbymasklayer` algorithm
  - [ ] Ensure Float32 output format
  - [ ] Write tests

#### 1.4.2 CRS Assignment
- [ ] Add method: `assign_crs_to_tif(tif_path, epsg)`
  - [ ] Use QGIS `gdal:assignprojection` or GDAL `gdal_edit.py`
  - [ ] Write tests

#### 1.4.3 Min/Max Extraction
- [ ] Add method: `get_raster_minmax(heightmap_tif, output_json)`
  - [ ] Use rasterio to compute statistics
  - [ ] Save to JSON for Unity import
  - [ ] Optional: Update Excel file if provided
  - [ ] Write tests

#### 1.4.4 Overlay Export
- [ ] Add method: `export_overlays(inner_tif, outer_tif, providers, size)`
  - [ ] Generate satellite overlays (Google/Bing) - may require external API
  - [ ] Or use QGIS XYZ tile layers if available
  - [ ] Export as TIF at specified size (default 16000)
  - [ ] Write tests (may need mocks for external APIs)

---

### Phase 1.5: Stage 5 - Unity Conversion (Week 4)

#### 1.5.1 RAW Conversion
- [ ] Create `pipeline/stage5_unity.py` module
  - [ ] Implement `UnityConverter` class
  - [ ] Add method: `heightmap_tif_to_raw(input_tif, min, max, output_raw, size)`
  - [ ] Use GDAL to read TIF, normalize to 0-65535 range
  - [ ] Convert to 16-bit unsigned integer
  - [ ] Write as binary RAW file (4097x4097 default)
  - [ ] Write tests

#### 1.5.2 Overlay JPG Conversion
- [ ] Add method: `overlay_tif_to_jpg(overlay_tifs, output_size, quality)`
  - [ ] Use GDAL or PIL to convert TIF to JPG
  - [ ] Resize to specified dimensions (8192x8192 default)
  - [ ] Set JPEG quality (95 default)
  - [ ] Write tests

---

### Phase 1.6: Validation and Integration (Week 5)

#### 1.6.1 Validation Module
- [ ] Create `pipeline/validation.py` module
  - [ ] Implement `OutputValidator` class
  - [ ] Add checks:
    - [ ] Required files exist
    - [ ] CRS consistency across files
    - [ ] RAW dimensions are 4097x4097
    - [ ] Overlay JPG dimensions are 8192x8192
    - [ ] Files are not empty/corrupted
  - [ ] Generate validation report
  - [ ] Write comprehensive tests

#### 1.6.2 Client Integration
- [ ] Update `client.py` to use all pipeline modules
  - [ ] Implement `setup_project()` method
  - [ ] Implement `merge_dem_tiles()` method
  - [ ] Implement `create_heightmaps()` method
  - [ ] Implement `convert_for_unity()` method
  - [ ] Implement `validate()` method
  - [ ] Add error handling and recovery
  - [ ] Add progress tracking integration

#### 1.6.3 CLI Integration
- [ ] Update `cli.py` commands
  - [ ] Add `--dem-paths` option for DEM tile input
  - [ ] Add `--inner-size` and `--outer-size` options
  - [ ] Add `--crs` option for manual CRS override
  - [ ] Add `--template-qgz` option
  - [ ] Add `--resume` option for resumable runs
  - [ ] Improve error messages and user feedback

---

### Phase 1.7: Testing and Documentation (Week 6)

#### 1.7.1 Test Suite
- [ ] Create comprehensive test suite
  - [ ] Unit tests for each pipeline module
  - [ ] Integration tests with sample data
  - [ ] Mock QGIS process for CI/CD
  - [ ] Test error handling and edge cases
  - [ ] Test workspace management
  - [ ] Test run tracking and resumability

#### 1.7.2 Documentation
- [ ] Update README.md with:
  - [ ] Complete usage examples
  - [ ] QGIS installation instructions
  - [ ] GDAL installation instructions
  - [ ] Sample workflow walkthrough
  - [ ] Troubleshooting guide
- [ ] Add docstrings to all modules
- [ ] Create example configuration files
- [ ] Add architecture diagrams if needed

#### 1.7.3 Example Data
- [ ] Create or document sample test data
  - [ ] Small DEM tile samples
  - [ ] Example shapefiles
  - [ ] Expected output examples
  - [ ] Test fixtures for unit tests

---

## Technical Decisions Needed

### 1. QGIS Process Integration
- **Decision**: Use `qgis_process` CLI (recommended) or PyQGIS bindings?
- **Recommendation**: Start with `qgis_process` CLI for better automation and no GUI dependency
- **Action**: Implement `QGISProcess` wrapper class

### 2. Overlay Generation
- **Decision**: How to generate Google/Bing satellite overlays?
- **Options**:
  - Use QGIS XYZ tile layers (if available)
  - Use external APIs (Google Maps, Bing Maps) - requires API keys
  - Use existing satellite imagery if provided
- **Recommendation**: Start with existing imagery, add API integration later
- **Action**: Make overlay generation optional in Stage 4

### 3. Run Resumability
- **Decision**: How detailed should context tracking be?
- **Recommendation**: Track stage completion and intermediate outputs
- **Action**: Implement `context.json` with stage status and file paths

### 4. Error Recovery
- **Decision**: How to handle partial failures?
- **Recommendation**: Allow resuming from last completed stage
- **Action**: Implement stage-level checkpoints

---

## Dependencies to Verify

- [ ] QGIS installation and `qgis_process` availability
- [ ] GDAL installation and Python bindings (rasterio, geopandas)
- [ ] Test with sample DEM files
- [ ] Verify CRS detection accuracy
- [ ] Test RAW file format compatibility with Unity

---

## Success Criteria

- [ ] All 5 stages implemented and tested
- [ ] CLI can run complete pipeline end-to-end
- [ ] Output files match OPCD workspace structure
- [ ] Validation passes for all required outputs
- [ ] Documentation complete and accurate
- [ ] Test suite passes with >80% coverage

---

## Notes

- Follow the same architectural patterns as `phase2a` for consistency
- Use similar error handling and logging patterns
- Keep configuration system similar to `Phase2AConfig`
- Consider future MCP integration but focus on standalone CLI first
- All operations should be idempotent where possible (safe to re-run)
