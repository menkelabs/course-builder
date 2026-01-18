# Embabel Automation Plan for OPCD Course Builder

## Overview

This document outlines automation for the **Open Platform Course Designer (OPCD)** workflow using **Embabel** as the orchestration layer with **MCP tools** for each application in the pipeline. The goal is to automate the "None to Done" process of creating golf courses for GSPro and other 3D applications.

---

## The OPCD Workflow (None to Done)

The complete workflow consists of 24 steps across multiple applications:

```
LIDAR → Unity (Terrain) → Inkscape (SVG) → Unity (PNG) → Blender (Mesh) → Unity (Final) → GreenKeeper
```

---

## Step-by-Step Workflow with MCP Tool Mapping

### Phase 1: Terrain Creation (Steps 1-2)

| Step | Manual Process | MCP Tool |
|------|----------------|----------|
| 1 | Download and follow tutorial for creating heightmap from LIDAR data | `lidar_to_heightmap` |
| 2 | Set up Terrain in Unity with LIDAR and course dimensions | `unity_setup_terrain` |

#### MCP Tools - LIDAR/GIS Processing

```yaml
lidar_to_heightmap:
  description: "Convert LIDAR data to Unity-compatible heightmap"
  inputs:
    - lidar_source: "URL or file path to LIDAR data"
    - bounds: "Geographic bounds of the course"
    - resolution: "Heightmap resolution"
  outputs:
    - heightmap_raw: "RAW heightmap file"
    - dimensions: "Real-world dimensions for Unity"
```

#### MCP Tools - Unity Terrain Setup

```yaml
unity_setup_terrain:
  description: "Create and configure Unity terrain from heightmap"
  inputs:
    - heightmap: "Path to heightmap file"
    - dimensions: "Width, length, height values"
    - project_path: "Unity project location"
  outputs:
    - terrain_object: "Configured Unity terrain"
    - scene: "Scene with terrain ready for overlay"
```

---

### Phase 2: Course Tracing in Inkscape (Steps 3-4)

| Step | Manual Process | MCP Tool |
|------|----------------|----------|
| 3 | Trace Course using Inkscape | `inkscape_trace_course` |
| 4 | Export Course as PNG for opening in Unity | `inkscape_export_png` |

#### MCP Tools - Inkscape Automation

```yaml
inkscape_create_project:
  description: "Set up new Inkscape file with OPCD palette and layers"
  inputs:
    - satellite_image: "Overlay image of the course"
    - course_name: "Name for the project"
  outputs:
    - inkscape_file: "Configured .svg file with layers for each hole"

inkscape_create_layer:
  description: "Create a hole layer with proper naming"
  inputs:
    - file: "Inkscape SVG file"
    - hole_number: "1-18, 98 (cart paths), or 99 (outer mesh)"
  outputs:
    - layer: "New layer added to SVG"

inkscape_draw_shape:
  description: "Draw a course feature shape"
  inputs:
    - file: "Inkscape SVG file"
    - layer: "Target layer"
    - shape_type: "fairway|rough|semi_rough|deep_rough|green|fringe|bunker|water|tee"
    - points: "Array of coordinate points"
    - fill_color: "OPCD palette color"
  outputs:
    - shape: "Shape added to layer"

inkscape_create_fringe:
  description: "Create fringe by duplicating and insetting a shape"
  inputs:
    - file: "Inkscape SVG file"
    - source_shape: "Shape to duplicate (e.g., green)"
    - inset_amount: "Inset distance for fringe"
  outputs:
    - fringe_shape: "New fringe shape"

inkscape_union_shapes:
  description: "Union meshes to connect features (e.g., tee boxes)"
  inputs:
    - file: "Inkscape SVG file"
    - shapes: "Array of shapes to union"
  outputs:
    - unified_shape: "Combined shape"

inkscape_fix_nodes:
  description: "Fix problematic nodes (autosmooth, remove duplicates)"
  inputs:
    - file: "Inkscape SVG file"
    - shape: "Shape to fix"
  outputs:
    - fixed_shape: "Shape with corrected nodes"

inkscape_export_png:
  description: "Export course as PNG for Unity overlay"
  inputs:
    - file: "Inkscape SVG file"
    - resolution: "Export resolution"
  outputs:
    - png_file: "Exported PNG image"
```

---

### Phase 3: Unity Terrain Refinement (Steps 5-7)

| Step | Manual Process | MCP Tool |
|------|----------------|----------|
| 5 | Place Exported PNG in first paint slot on Terrain in Unity | `unity_apply_terrain_overlay` |
| 6 | Adjust contours of Terrain and modify SVG file as needed | `unity_adjust_terrain_contours` |
| 7 | Export Terrain using ExportTerrain.cs - export as Terrain.obj | `unity_export_terrain` |

#### MCP Tools - Unity Terrain Operations

```yaml
unity_apply_terrain_overlay:
  description: "Apply PNG overlay to terrain paint slot"
  inputs:
    - project_path: "Unity project"
    - terrain: "Target terrain object"
    - png_file: "Course overlay PNG"
    - paint_slot: "Slot number (typically 0)"
  outputs:
    - terrain: "Terrain with overlay applied"

unity_adjust_terrain_contours:
  description: "Modify terrain height at specific locations"
  inputs:
    - project_path: "Unity project"
    - terrain: "Target terrain"
    - adjustments: "Array of {position, height, radius, falloff}"
  outputs:
    - terrain: "Modified terrain"

unity_export_terrain:
  description: "Export terrain as OBJ using ExportTerrain.cs"
  inputs:
    - project_path: "Unity project"
    - terrain: "Terrain to export"
    - resolution: "full|half|quarter"
    - output_path: "Where to save Terrain.obj"
  outputs:
    - terrain_obj: "Exported OBJ file"
```

---

### Phase 4: SVG Conversion (Step 8)

| Step | Manual Process | MCP Tool |
|------|----------------|----------|
| 8 | Run SVG file through GSProSVGConvert.exe to get "svg-converted" file | `svg_convert` |

#### MCP Tools - SVG Conversion

```yaml
svg_convert:
  description: "Run GSProSVGConvert.exe to prepare SVG for Blender"
  inputs:
    - svg_file: "Original Inkscape SVG"
  outputs:
    - converted_svg: "SVG file ready for Blender import"
```

---

### Phase 5: Blender Mesh Operations (Steps 9-16)

| Step | Manual Process | MCP Tool |
|------|----------------|----------|
| 9 | Open OPCDcourseconversion.blend file (Blender 2.83 LTS) | `blender_open_opcd_template` |
| 10 | Install Boundary Align Remesh, Mesh Tools, Loop Tools, OPCD Blender Tools | `blender_install_addons` |
| 11 | Import SVG | `blender_import_svg` |
| 12 | Import Terrain.obj | `blender_import_terrain` |
| 13 | Convert Mats and Cut | `blender_convert_and_cut` |
| 14 | Convert Meshes (conform to terrain) | `blender_convert_meshes` |
| 15 | Add Bulkheads, Curbs, WaterPlanes or other peripherals | `blender_add_peripherals` |
| 16 | Export FBX files | `blender_export_fbx` |

#### MCP Tools - Blender Operations

```yaml
blender_open_opcd_template:
  description: "Open the OPCDcourseconversion.blend template file"
  inputs:
    - template_path: "Path to OPCDcourseconversion.blend"
  outputs:
    - blender_session: "Active Blender session with template"

blender_install_addons:
  description: "Install required OPCD addons if not present"
  inputs:
    - addons:
      - "Boundary Align Remesh"
      - "Mesh Tools"
      - "Loop Tools"
      - "OPCD Blender Tools"
  outputs:
    - status: "Addons installed and enabled"

blender_import_svg:
  description: "Import converted SVG file"
  inputs:
    - svg_file: "Path to svg-converted file"
  outputs:
    - svg_curves: "Imported SVG curves in Blender"

blender_import_terrain:
  description: "Import Terrain.obj from Unity export"
  inputs:
    - terrain_obj: "Path to Terrain.obj"
  outputs:
    - terrain_mesh: "Imported terrain mesh"

blender_convert_and_cut:
  description: "Run Convert Mats and Cut operation from OPCD Tools"
  inputs:
    - svg_curves: "Imported SVG"
    - terrain_mesh: "Imported terrain"
  outputs:
    - cut_meshes: "Meshes cut by hole"

blender_convert_meshes:
  description: "Conform shapes to terrain surface"
  inputs:
    - cut_meshes: "Cut mesh shapes"
    - terrain_mesh: "Terrain to conform to"
  outputs:
    - conformed_meshes: "Meshes projected onto terrain"

blender_fix_donut:
  description: "Fix cart path donut corruption (Hole98)"
  inputs:
    - cart_path_mesh: "Cart path with donut issue"
  outputs:
    - fixed_mesh: "Corrected cart path mesh"

blender_add_curbs:
  description: "Add curbs to cart paths"
  inputs:
    - cart_path: "Cart path mesh"
    - curb_height: "Height of curbs"
    - curb_width: "Width of curbs"
  outputs:
    - cart_path_with_curbs: "Cart path with curbs added"

blender_add_bulkhead:
  description: "Add bulkhead to water features"
  inputs:
    - water_mesh: "Water feature mesh"
    - bulkhead_style: "Style parameters"
  outputs:
    - water_with_bulkhead: "Water with bulkhead edging"

blender_add_water_plane:
  description: "Add water plane to water hazards"
  inputs:
    - water_boundary: "Water feature boundary"
    - water_level: "Height of water surface"
  outputs:
    - water_plane: "Water plane mesh"

blender_retopo_hole99:
  description: "Retopologize Hole99 outer mesh"
  inputs:
    - outer_mesh: "Hole99 mesh"
  outputs:
    - retopo_mesh: "Clean retopologized outer mesh"

blender_export_fbx:
  description: "Export all meshes as FBX files"
  inputs:
    - meshes: "All course meshes"
    - output_directory: "Export location"
    - per_hole: "Export per hole or combined"
  outputs:
    - fbx_files: "Array of exported FBX files"
```

---

### Phase 6: Unity Final Assembly (Steps 17-22)

| Step | Manual Process | MCP Tool |
|------|----------------|----------|
| 17 | Import FBX files into Unity | `unity_import_fbx` |
| 18 | Add colliders to FBX files | `unity_add_colliders` |
| 19 | Add FBX files to the Unity Scene | `unity_place_meshes` |
| 20 | Add Materials to the Meshes (drag/drop or SetMaterials.cs) | `unity_apply_materials` |
| 21 | Plant vegetation and other objects | `unity_place_vegetation` |
| 22 | Course Asset Bundle Build Out | `unity_build_asset_bundle` |

#### MCP Tools - Unity Final Assembly

```yaml
unity_import_fbx:
  description: "Import FBX files from Blender export"
  inputs:
    - project_path: "Unity project"
    - fbx_files: "Array of FBX file paths"
    - import_settings: "FBX import configuration"
  outputs:
    - imported_assets: "FBX assets in Unity"

unity_add_colliders:
  description: "Add mesh colliders to course meshes"
  inputs:
    - project_path: "Unity project"
    - meshes: "Meshes to add colliders to"
    - collider_type: "mesh|box|convex"
  outputs:
    - meshes_with_colliders: "Meshes with colliders attached"

unity_place_meshes:
  description: "Position FBX meshes in the scene"
  inputs:
    - project_path: "Unity project"
    - scene: "Target scene"
    - meshes: "Meshes to place"
    - alignment: "Terrain alignment settings"
  outputs:
    - placed_objects: "Game objects in scene"

unity_apply_materials:
  description: "Apply materials using SetMaterials.cs or direct assignment"
  inputs:
    - project_path: "Unity project"
    - mesh_material_map:
      - mesh: "fairway_*"
        material: "FairwayMaterial"
      - mesh: "rough_*"
        material: "RoughMaterial"
      - mesh: "bunker_*"
        material: "BunkerMaterial"
      # ... etc
  outputs:
    - materialized_meshes: "Meshes with materials applied"

unity_setup_satellite_shader:
  description: "Configure satellite imagery shader"
  inputs:
    - project_path: "Unity project"
    - satellite_image: "Satellite overlay image"
    - blend_settings: "Shader blend configuration"
  outputs:
    - shader_configured: "Satellite shader ready"

unity_place_vegetation:
  description: "Place trees, bushes, grass using Vegetation Studio Pro or manual"
  inputs:
    - project_path: "Unity project"
    - vegetation_rules:
      - type: "tree"
        density: 0.3
        areas: ["rough", "deep_rough"]
      - type: "grass"
        density: 0.8
        areas: ["fairway", "rough"]
  outputs:
    - vegetation_placed: "Vegetation in scene"

unity_setup_3d_grass:
  description: "Configure Stixx 3D Grass shader"
  inputs:
    - project_path: "Unity project"
    - grass_settings: "3D grass configuration"
  outputs:
    - grass_configured: "3D grass shader active"

unity_setup_water_reflections:
  description: "Configure water reflections (PIDI Water or reflection probes)"
  inputs:
    - project_path: "Unity project"
    - water_meshes: "Water plane meshes"
    - reflection_type: "pidi|probes"
  outputs:
    - water_configured: "Water with reflections"

unity_setup_gpu_instancer:
  description: "Configure GPU Instancer for performance"
  inputs:
    - project_path: "Unity project"
    - objects_to_instance: "Vegetation and repeated objects"
  outputs:
    - instancing_configured: "GPU Instancer set up"

unity_build_asset_bundle:
  description: "Build course asset bundle for GSPro"
  inputs:
    - project_path: "Unity project"
    - scene: "Course scene"
    - bundle_name: "Output bundle name"
    - platform: "Target platform"
  outputs:
    - asset_bundle: "Built .assetbundle file"
```

---

### Phase 7: GreenKeeper Setup (Steps 23-24)

| Step | Manual Process | MCP Tool |
|------|----------------|----------|
| 23 | Use GSP GreenKeeper to add Tees, Pins, Shotpoints, and Hazards | `greenkeeper_configure` |
| 24 | Using Paid Assets - GPU Instancer and PIDI Water | (covered in Unity tools above) |

#### MCP Tools - GreenKeeper

```yaml
greenkeeper_add_tees:
  description: "Add tee positions for each hole"
  inputs:
    - course: "Course data"
    - tees_per_hole:
      - hole: 1
        positions:
          - color: "black"
            position: [x, y, z]
          - color: "blue"
            position: [x, y, z]
          # ... etc
  outputs:
    - tees_configured: "Tee positions saved"

greenkeeper_add_pins:
  description: "Add pin positions using slope shader guidance"
  inputs:
    - course: "Course data"
    - pins_per_hole:
      - hole: 1
        positions:
          - id: "A"
            position: [x, y, z]
          - id: "B"
            position: [x, y, z]
  outputs:
    - pins_configured: "Pin positions saved"

greenkeeper_add_shotpoints:
  description: "Add shotpoint/aim point markers"
  inputs:
    - course: "Course data"
    - shotpoints: "Array of shotpoint definitions"
  outputs:
    - shotpoints_configured: "Shotpoints saved"

greenkeeper_add_hazards:
  description: "Define hazard boundaries and types"
  inputs:
    - course: "Course data"
    - hazards:
      - type: "water"
        boundary: "polygon points"
      - type: "bunker"
        boundary: "polygon points"
      - type: "ob"
        boundary: "polygon points"
  outputs:
    - hazards_configured: "Hazards saved"

greenkeeper_export:
  description: "Export GreenKeeper data for GSPro"
  inputs:
    - course: "Course data"
    - format: "GSPro format"
  outputs:
    - greenkeeper_file: "Exported GK file"
```

---

## Embabel Orchestration

Embabel coordinates the entire None to Done workflow, calling MCP tools in sequence.

### Complete Workflow Definition

```yaml
workflow: opcd_none_to_done
name: "OPCD Golf Course Creation"

phases:
  - name: terrain_creation
    steps:
      - tool: lidar_to_heightmap
        inputs:
          lidar_source: "${input.lidar_url}"
          bounds: "${input.course_bounds}"
      - tool: unity_setup_terrain
        inputs:
          heightmap: "${lidar_to_heightmap.output.heightmap_raw}"
          dimensions: "${lidar_to_heightmap.output.dimensions}"
    gate: terrain_ready

  - name: course_tracing
    steps:
      - tool: inkscape_create_project
        inputs:
          satellite_image: "${input.satellite_image}"
          course_name: "${input.course_name}"
      - tool: inkscape_trace_course  # Multiple calls per hole
        for_each: hole in 1..18
      - tool: inkscape_export_png
    gate: svg_complete

  - name: terrain_refinement
    steps:
      - tool: unity_apply_terrain_overlay
      - tool: unity_adjust_terrain_contours
      - tool: unity_export_terrain
        inputs:
          resolution: "half"
    gate: terrain_exported

  - name: svg_conversion
    steps:
      - tool: svg_convert
    gate: svg_converted

  - name: blender_processing
    steps:
      - tool: blender_open_opcd_template
      - tool: blender_import_svg
      - tool: blender_import_terrain
      - tool: blender_convert_and_cut
      - tool: blender_convert_meshes
      - tool: blender_add_curbs
        if: has_cart_paths
      - tool: blender_add_bulkhead
        if: has_water
      - tool: blender_add_water_plane
        if: has_water
      - tool: blender_export_fbx
    gate: fbx_exported

  - name: unity_assembly
    steps:
      - tool: unity_import_fbx
      - tool: unity_add_colliders
      - tool: unity_place_meshes
      - tool: unity_apply_materials
      - tool: unity_place_vegetation
      - tool: unity_setup_water_reflections
        if: has_water
      - tool: unity_setup_gpu_instancer
      - tool: unity_build_asset_bundle
    gate: bundle_built

  - name: greenkeeper_setup
    steps:
      - tool: greenkeeper_add_tees
      - tool: greenkeeper_add_pins
      - tool: greenkeeper_add_shotpoints
      - tool: greenkeeper_add_hazards
      - tool: greenkeeper_export
    gate: course_complete

output:
  asset_bundle: "${unity_build_asset_bundle.output.asset_bundle}"
  greenkeeper_data: "${greenkeeper_export.output.greenkeeper_file}"
  status: "DONE"
```

---

## MCP Server Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Embabel Orchestrator                      │
│              (Drives None to Done Workflow)                  │
└──────────────────────────┬──────────────────────────────────┘
                           │
       ┌───────────────────┼───────────────────┐
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  LIDAR/GIS  │    │  Inkscape   │    │   Blender   │
│ MCP Server  │    │ MCP Server  │    │ MCP Server  │
└─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│    Unity    │    │ SVG Convert │    │ GreenKeeper │
│ MCP Server  │    │ MCP Server  │    │ MCP Server  │
└─────────────┘    └─────────────┘    └─────────────┘
```

### MCP Server Responsibilities

| Server | Application | Key Functions |
|--------|-------------|---------------|
| `lidar-mcp` | LIDAR Processing | Heightmap generation from GIS data |
| `inkscape-mcp` | Inkscape | SVG creation, shape drawing, export |
| `svg-convert-mcp` | GSProSVGConvert | SVG preparation for Blender |
| `blender-mcp` | Blender 2.83 LTS | Mesh conversion, terrain projection, FBX export |
| `unity-mcp` | Unity | Terrain, materials, vegetation, asset bundles |
| `greenkeeper-mcp` | GSP GreenKeeper | Tees, pins, hazards, course data |

---

## Implementation Roadmap

### Phase 1: Core Pipeline Tools

- [ ] `inkscape-mcp` - SVG creation and export
- [ ] `blender-mcp` - Core mesh operations (import, cut, convert, export)
- [ ] `unity-mcp` - Terrain and FBX import

### Phase 2: Automation Enhancement

- [ ] `svg-convert-mcp` - GSProSVGConvert wrapper
- [ ] `blender-mcp` - Peripherals (curbs, bulkheads, water planes)
- [ ] `unity-mcp` - Materials and colliders

### Phase 3: Advanced Features

- [ ] `lidar-mcp` - Heightmap generation
- [ ] `unity-mcp` - Vegetation, shaders, GPU Instancer
- [ ] `greenkeeper-mcp` - Full GreenKeeper automation

### Phase 4: Embabel Integration

- [ ] Workflow orchestration
- [ ] Progress tracking and checkpoints
- [ ] Error recovery and retry logic
- [ ] User prompts for manual steps

---

## Special Considerations

### Hole 98 and Hole 99 Concepts

- **Hole 99**: Outer mesh that spans multiple holes (deep rough around course)
- **Hole 98**: Features that cut through other objects (cart paths)

These require special handling in both Inkscape and Blender MCP tools.

### Donut Fix Workflow

Cart paths that loop create "donuts" that must be fixed in Blender:

```yaml
blender_fix_donut:
  trigger: cart_path_has_loop
  steps:
    - hide_hole99_mesh
    - select_cart_path
    - enter_edit_mode
    - remove_corrupt_face
    - exit_edit_mode
    - unhide_hole99_mesh
```

### Paid Asset Integration

Tools should support optional paid assets:
- **GPU Instancer** - Performance optimization
- **PIDI Water** - Water reflections
- **Vegetation Studio Pro** - Advanced vegetation
- **Stixx 3D Grass** - Grass rendering

---

## References

- [OPCD Documentation](https://docs.google.com/document/d/1InsfFuOrAH4l2S6RnTy17_O8FPXwt_EA_jKLvW4Ky80)
- [None to Done Video Series](https://docs.google.com/document/d/1bwNRByfPQNbUOWfKymXvdoWq9QP9-1R0U1GaJf5z9fU)
- [OPCD Discord](https://discord.gg/4ZhJzwx)
- [Zeros and Ones GCD Tutorials](https://zerosandonesgcd.com/)
