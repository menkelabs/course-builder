# Phase 1 Hybrid Workflow Plan
## Human-Guided Selection + Automated Processing

This plan outlines a hybrid approach where users visually select the course area in QGIS, then the script automates the rest of the terrain preparation pipeline.

## Workflow Overview

```
1. User Action: Open QGIS → Load imagery → Draw course boundary
2. Script Action: Read boundary → Extract coordinates → Continue automation
3. Automated: DEM processing → Heightmaps → Unity conversion
```

## Architecture

### Phase 1: Interactive Selection (Human)

**User Steps:**
1. Launch QGIS with pre-configured project template
2. Load satellite imagery (Google/Bing XYZ tiles or local image)
3. Navigate to golf course location
4. Draw/select course boundary (polygon or rectangle)
5. Save selection as shapefile or confirm coordinates
6. Trigger automated processing

**Script Support:**
- Launch QGIS with template project
- Provide instructions overlay
- Monitor for user selection
- Read selection from QGIS project or shapefile

### Phase 2: Automated Processing (Script)

**Script Steps:**
1. Read boundary coordinates from QGIS output
2. Extract geographic bounds (north, south, east, west)
3. Find/download appropriate DEM tiles for area
4. Merge DEM tiles
5. Create inner/outer heightmaps
6. Generate overlays
7. Convert to Unity format

## Implementation Plan

### 1. QGIS Project Template

**File:** `phase1/resources/template_course_selection.qgz`

**Template includes:**
- Pre-configured XYZ tile layers (Google Satellite, Bing Aerial)
- Base map layers for reference
- Instructions layer (text annotations)
- Empty boundary layer (for user to draw)
- Coordinate display plugin enabled

**Template setup:**
```python
# Create template with:
# - Google Satellite XYZ: https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}
# - Bing Aerial XYZ: https://ecn.t0.tiles.virtualearth.net/tiles/a{q}.jpeg?g=1
# - Boundary layer (polygon, editable)
# - Instructions text layer
```

### 2. Interactive Selection Module

**File:** `phase1/pipeline/interactive_selection.py`

**Functions:**
- `launch_qgis_with_template(template_path, workspace_path)` - Opens QGIS GUI
- `wait_for_user_selection(project_path, timeout=None)` - Monitors for boundary
- `read_boundary_from_project(project_path)` - Extracts coordinates
- `read_boundary_from_shapefile(shapefile_path)` - Alternative input
- `validate_boundary(bounds)` - Checks bounds are valid

**User Interaction Flow:**
1. Script launches QGIS with template
2. User sees instructions: "Draw a polygon around the golf course"
3. User draws boundary using QGIS drawing tools
4. User saves/confirms selection
5. Script detects saved shapefile or reads from project
6. Script extracts bounds and continues

### 3. Coordinate Extraction

**File:** `phase1/pipeline/boundary_extraction.py`

**Functions:**
- `extract_bounds_from_shapefile(shapefile_path)` - Reads polygon bounds
- `extract_bounds_from_qgis_project(project_path, layer_name)` - Reads from QGIS project
- `bounds_to_geographic(bounds, crs)` - Converts to lat/lon
- `geographic_to_golfcourse_bounds(geographic_bounds)` - Formats for Java backend

**Output Format:**
```python
{
    "northLat": 40.5234,
    "southLat": 40.5123,
    "eastLon": -74.3456,
    "westLon": -74.3567,
    "crs": "EPSG:4326",
    "area_km2": 2.5
}
```

### 4. Integration with Java Backend

**Update:** `course-builder/src/main/java/com/coursebuilder/tool/golfcourse/LidarMcpTool.java`

**New method:**
```java
public ToolResult interactiveCourseSelection(String courseId) {
    // Launch Phase 1 interactive selection
    // Wait for user to select boundary in QGIS
    // Read bounds from QGIS output
    // Store in GolfCourse.GeographicBounds
    // Return success with bounds
}
```

**Workflow:**
1. User: "Create new course 'Pine Valley'"
2. Agent: "I'll help you set up the course. Let me open QGIS for you to select the area."
3. Script: Launches QGIS with template
4. User: Draws boundary in QGIS
5. Script: Extracts bounds, saves to workspace
6. Backend: Reads bounds, stores in `GolfCourse.GeographicBounds`
7. Agent: "Great! I've captured the course boundary. Now I'll process the terrain..."

### 5. CLI Command for Interactive Mode

**File:** `phase1/cli.py`

**New command:**
```python
@cli.command()
@click.option("--course-name", required=True)
@click.option("--workspace", "-o", type=Path, default=Path("workspace"))
def interactive_select(course_name: str, workspace: Path):
    """
    Launch QGIS for interactive course boundary selection.
    
    This opens QGIS with a template project. Draw a polygon around
    the golf course, then save it. The script will continue automatically.
    """
    # Launch QGIS
    # Wait for selection
    # Extract bounds
    # Save to workspace
    # Continue with automated pipeline
```

## Detailed Implementation Steps

### Step 1: Create QGIS Template Project

**Module:** `phase1/pipeline/qgis_template.py`

```python
def create_selection_template(output_path: Path):
    """Create QGIS project template for course selection."""
    # Initialize QGIS
    from pipeline.qgis_env import setup_qgis_environment
    setup_qgis_environment()
    
    from qgis.core import QgsProject, QgsVectorLayer, QgsRasterLayer
    
    project = QgsProject.instance()
    
    # Add Google Satellite layer
    google_url = "type=xyz&url=https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"
    google_layer = QgsRasterLayer(google_url, "Google Satellite", "wms")
    project.addMapLayer(google_layer)
    
    # Create boundary layer (polygon, editable)
    boundary_layer = QgsVectorLayer(
        "Polygon?crs=EPSG:4326",
        "Course Boundary",
        "memory"
    )
    boundary_layer.setEditable(True)
    project.addMapLayer(boundary_layer)
    
    # Save template
    project.write(output_path)
```

### Step 2: Launch QGIS with Template

**Module:** `phase1/pipeline/qgis_launcher.py`

```python
import subprocess
from pathlib import Path

def launch_qgis_with_template(template_path: Path, workspace_path: Path):
    """Launch QGIS GUI with template project."""
    # Copy template to workspace
    project_path = workspace_path / "course_selection.qgz"
    shutil.copy(template_path, project_path)
    
    # Launch QGIS
    subprocess.Popen([
        "qgis",
        str(project_path)
    ])
    
    return project_path

def wait_for_boundary_shapefile(workspace_path: Path, timeout=300):
    """Wait for user to save boundary shapefile."""
    boundary_path = workspace_path / "Shapefiles" / "Course_Boundary.shp"
    
    # Poll for file creation
    start_time = time.time()
    while not boundary_path.exists():
        if timeout and (time.time() - start_time) > timeout:
            raise TimeoutError("User did not save boundary within timeout")
        time.sleep(1)
    
    return boundary_path
```

### Step 3: Extract Coordinates

**Module:** `phase1/pipeline/boundary_extraction.py`

```python
import geopandas as gpd
from shapely.geometry import box

def extract_bounds_from_shapefile(shapefile_path: Path):
    """Extract geographic bounds from shapefile."""
    gdf = gpd.read_file(shapefile_path)
    
    # Get bounding box
    bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]
    
    return {
        "westLon": bounds[0],
        "southLat": bounds[1],
        "eastLon": bounds[2],
        "northLat": bounds[3],
        "crs": str(gdf.crs),
        "area_km2": gdf.geometry.area.sum() / 1e6  # Convert m² to km²
    }
```

### Step 4: Update Phase1Config

**File:** `phase1/config.py`

```python
@dataclass
class InteractiveConfig:
    """Configuration for interactive QGIS selection."""
    enable_interactive: bool = True
    template_qgz: Optional[Path] = None
    boundary_layer_name: str = "Course Boundary"
    selection_timeout: int = 300  # seconds
    auto_continue: bool = True  # Continue pipeline after selection

@dataclass
class Phase1Config:
    # ... existing fields ...
    interactive: InteractiveConfig = field(default_factory=InteractiveConfig)
    geographic_bounds: Optional[Dict[str, float]] = None  # From user selection
```

### Step 5: Update Client

**File:** `phase1/client.py`

```python
def interactive_course_selection(self) -> Dict[str, float]:
    """Launch QGIS for user to select course boundary."""
    logger.info("Launching QGIS for interactive course selection...")
    
    # Launch QGIS
    template_path = self.config.interactive.template_qgz
    if not template_path:
        template_path = self._create_default_template()
    
    project_path = launch_qgis_with_template(
        template_path,
        self.state.workspace_path
    )
    
    logger.info(f"QGIS opened with project: {project_path}")
    logger.info("Please draw a polygon around the golf course in QGIS.")
    logger.info("Save the boundary layer when finished.")
    
    # Wait for user selection
    boundary_path = wait_for_boundary_shapefile(
        self.state.workspace_path,
        timeout=self.config.interactive.selection_timeout
    )
    
    # Extract bounds
    bounds = extract_bounds_from_shapefile(boundary_path)
    self.config.geographic_bounds = bounds
    
    logger.info(f"Course boundary selected: {bounds}")
    return bounds

def run(self, interactive: bool = True) -> PipelineState:
    """Run pipeline with optional interactive selection."""
    if interactive and not self.config.geographic_bounds:
        # Step 1: Interactive selection
        bounds = self.interactive_course_selection()
        
        # Save bounds for Java backend
        self._save_bounds_to_json(bounds)
    
    # Step 2: Automated processing
    self.setup_project()
    # ... continue with automated steps ...
```

## User Experience Flow

### Scenario 1: CLI Interactive Mode

```bash
$ python -m phase1.cli interactive-select --course-name "Pine Valley" -o workspace/

[INFO] Creating QGIS project template...
[INFO] Launching QGIS...
[INFO] QGIS opened. Please follow these steps:
      1. Navigate to the golf course location
      2. Use the "Add Polygon" tool to draw around the course
      3. Save the layer when finished
[INFO] Waiting for boundary selection...
[INFO] ✓ Boundary detected!
[INFO] Extracted bounds: N:40.5234, S:40.5123, E:-74.3456, W:-74.3567
[INFO] Continuing with automated terrain processing...
[INFO] Stage 2: Setting up project...
[INFO] Stage 3: Merging DEM tiles...
...
```

### Scenario 2: Java Backend Integration

```java
// User: "Create new course 'Pine Valley'"
// Agent responds:
"Great! To set up the terrain, I need to know the course location.
I'll open QGIS for you to select the area visually.

[Launches QGIS with template]

Please:
1. Navigate to Pine Valley Golf Course
2. Draw a polygon around the course boundary
3. Save the selection

I'll continue automatically once you've saved the boundary."

// After user saves:
"Perfect! I've captured the course boundary.
Now I'll process the LIDAR data and create the heightmaps..."
```

## Benefits of Hybrid Approach

1. **Visual Accuracy** - Users can see exactly what area they're selecting
2. **Flexibility** - Works with any coordinate system, any imagery source
3. **User Control** - Users can adjust selection before committing
4. **Automation** - Once selected, everything else is automated
5. **Error Prevention** - Visual confirmation reduces coordinate errors

## Alternative: Non-Interactive Fallback

If QGIS GUI is not available (headless server), fall back to:
- Text input: `--bounds 40.5234,40.5123,-74.3456,-74.3567`
- Config file: `geographic_bounds` section
- Existing shapefile: `--boundary-shapefile path/to/boundary.shp`

## Files to Create/Modify

1. **New Files:**
   - `phase1/pipeline/interactive_selection.py` - QGIS launch and monitoring
   - `phase1/pipeline/boundary_extraction.py` - Coordinate extraction
   - `phase1/pipeline/qgis_template.py` - Template project creation
   - `phase1/resources/template_course_selection.qgz` - QGIS template
   - `phase1/HYBRID_WORKFLOW_PLAN.md` - This document

2. **Modified Files:**
   - `phase1/config.py` - Add `InteractiveConfig` and `geographic_bounds`
   - `phase1/client.py` - Add `interactive_course_selection()` method
   - `phase1/cli.py` - Add `interactive-select` command
   - `course-builder/.../LidarMcpTool.java` - Add interactive selection support

## Testing Plan

1. **Unit Tests:**
   - Template creation
   - Boundary extraction from shapefile
   - Coordinate conversion
   - Bounds validation

2. **Integration Tests:**
   - Launch QGIS (headless test with mock)
   - Full workflow: selection → extraction → processing
   - Fallback to text input

3. **Manual Testing:**
   - User draws boundary in QGIS
   - Verify bounds are extracted correctly
   - Verify pipeline continues automatically

## Next Steps

1. Implement QGIS template creation
2. Implement interactive selection launcher
3. Implement boundary extraction
4. Integrate with Phase 1 client
5. Add CLI command
6. Integrate with Java backend
7. Test end-to-end workflow
