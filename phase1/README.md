# Phase 1 - QGIS/GDAL Terrain Preparation

Automated terrain preparation for golf course creation using QGIS and GDAL. Processes DEM/DTM data to create heightmaps and overlays for Unity.

> **Note**: Phase 1 is one of several sections that will be developed as part of the complete course builder pipeline. See [plan.md](../plan.md) for the full automation plan and workflow overview.

## Features

- **DEM Processing**: Merge DEM/DTM tiles into unified terrain data
- **Heightmap Generation**: Create inner and outer heightmaps for Unity terrain
- **CRS Detection**: Automatically detect and set coordinate reference systems
- **Overlay Export**: Generate satellite overlays from multiple providers
- **Unity Conversion**: Convert heightmaps to Unity-compatible RAW format
- **Workspace Management**: Organized workspace structure following OPCD conventions

## Installation

1. Create a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies:
```bash
cd phase1
pip install -e .
```

3. Install QGIS and GDAL:
   - **QGIS**: Install QGIS Desktop (includes PyQGIS bindings) or use `qgis_process` CLI
   - **GDAL**: Install via system package manager or conda
   - See [QGIS Installation](https://qgis.org/download/) and [GDAL Installation](https://gdal.org/download.html)

## Usage

### Run Complete Pipeline

Run the full Phase 1 pipeline:

```bash
phase1 run --course-name MyCourse -o workspace/
```

**Options:**
- `-c, --config`: YAML or JSON configuration file
- `--course-name`: Course name
- `-o, --output`: Workspace output directory
- `-v, --verbose`: Enable verbose output

**Example with config file:**
```bash
phase1 run -c config.yaml -v
```

### Initialize Configuration File

Generate a default configuration file:

```bash
phase1 init-config -o config.yaml
```

**Options:**
- `-o, --output`: Output config file path (default: `phase1_config.yaml`)
- `--format`: Config file format: `yaml` or `json` (default: `yaml`)

### Validate Output

Validate pipeline output:

```bash
phase1 validate workspace/
```

### Display Pipeline Information

Show pipeline information and usage:

```bash
phase1 info
```

## Pipeline Stages

The Phase 1 pipeline consists of:

1. **Stage 2: Project Setup**
   - Initialize QGIS project
   - Set up workspace directory structure
   - Detect and set coordinate reference system (CRS)
   - Create inner and outer plot shapefiles

2. **Stage 3: DEM Merging**
   - Merge multiple DEM/DTM tiles into single TIF
   - Handle CRS transformations
   - Validate merged output

3. **Stage 4: Heightmap Creation**
   - Clip merged DEM to inner and outer boundaries
   - Export heightmaps as Float32 TIF
   - Generate satellite overlays (Google/Bing)
   - Extract min/max values for Unity

4. **Stage 5: Unity Conversion**
   - Convert heightmap TIF to Unity RAW format (4097x4097)
   - Convert overlay TIFs to JPEG (8192x8192)
   - Validate output dimensions

5. **Validation**
   - Check required files exist
   - Verify CRS consistency
   - Validate file dimensions and formats

## Workspace Structure

```
workspace/
├── DEM/                    # Input DEM/DTM tiles
├── Shapefiles/             # Inner and outer plot boundaries
│   ├── Inner.*
│   └── Outer.*
├── TIF/                    # Merged DEM
│   └── <Course>_merged.tif
├── Heightmap/
│   ├── INNER/
│   │   ├── <Course>_Lidar_Surface_Inner.tif
│   │   └── <Course>_Lidar_Surface_Inner.raw
│   └── OUTER/
│       ├── <Course>_Lidar_Surface_Outer.tif
│       └── <Course>_Lidar_Surface_Outer.raw
├── Overlays/               # Satellite overlays
│   ├── google_*.jpg
│   └── bing_*.jpg
└── Runs/                   # Run logs and traces
    └── <timestamp>/
        ├── run.json
        └── trace.jsonl
```

## Configuration

The pipeline can be configured via:
- CLI options (see `phase1 run --help`)
- YAML/JSON config files (use `-c` option)
- `Phase1Config` class in `phase1/config.py`

Key configuration options:
- Course name
- Workspace directory structure
- QGIS process path and template project
- GDAL tool paths
- Heightmap and overlay dimensions
- CRS settings

## Development

The project uses:
- **Python 3.9+**
- **pytest** for testing
- **Click** for CLI
- **Rich** for console output
- **QGIS** for GIS operations (via PyQGIS or qgis_process)
- **GDAL** for raster processing

See `qgis-plan.md` for detailed design specification.
