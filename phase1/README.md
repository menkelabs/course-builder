# Phase 1 - QGIS/GDAL Terrain Preparation

Automated terrain preparation for golf course creation using QGIS and GDAL. Processes DEM/DTM data to create heightmaps and overlays for Unity.

![QGIS Interactive Selection](docs/qgis.png)

*Interactive course boundary selection in QGIS with satellite imagery and boundary layer.*

[![QGIS Automation Tutorial](https://img.youtube.com/vi/w6FlVZjydtY/0.jpg)](https://youtu.be/w6FlVZjydtY?si=2da0Iwy3OhZfHy2m)

*Watch the QGIS automation tutorial video*

> **Note**: Phase 1 is one of several sections that will be developed as part of the complete course builder pipeline. See the [main README](../README.md) for an overview of all components and [plan.md](../plan.md) for the full automation specification.

## Features

- **DEM Processing**: Merge DEM/DTM tiles into unified terrain data
- **Heightmap Generation**: Create inner and outer heightmaps for Unity terrain
- **CRS Detection**: Automatically detect and set coordinate reference systems
- **Overlay Export**: Generate satellite overlays from multiple providers
- **Unity Conversion**: Convert heightmaps to Unity-compatible RAW format
- **Workspace Management**: Organized workspace structure following OPCD conventions

## Installation

This project uses a **shared virtual environment at the project root**.

1. Activate the root virtual environment:
```bash
# From project root
cd /path/to/course-builder
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install Phase 1 in editable mode:
```bash
cd phase1
pip install -e .
```

**Note**: The `.venv` is located at the project root (`course-builder/.venv`), not in the `phase1/` directory.

3. Install QGIS and GDAL:
   - **QGIS**: Run automated setup: `python -m phase1.qgis_setup.setup_qgis`
   - **GDAL**: Install via system package manager or conda
   - See [qgis_setup/QGIS_SETUP.md](qgis_setup/QGIS_SETUP.md) for manual installation

## Usage

### Interactive Course Selection (Recommended)

**Important:** Activate the root virtual environment first:
```bash
# From project root
source .venv/bin/activate
```

Then launch QGIS to visually select the course boundary:

```bash
python -m phase1.cli interactive-select --course-name MyCourse -o workspace/
```

This will:
1. Open QGIS with satellite imagery
2. Let you draw a polygon around the golf course
3. Automatically extract coordinates
4. Save bounds for automated processing

### Run Complete Pipeline

Run the full Phase 1 pipeline (includes interactive selection if no bounds exist):

```bash
# Activate venv first
source .venv/bin/activate

# Run pipeline
python -m phase1.cli run --course-name MyCourse -o workspace/
```

**Note:** See [QUICK_START.md](QUICK_START.md) for detailed setup instructions.

**Options:**
- `-c, --config`: YAML or JSON configuration file
- `--course-name`: Course name
- `-o, --output`: Workspace output directory
- `-v, --verbose`: Enable verbose output

**Example with config file:**
```bash
# Activate venv first
source .venv/bin/activate

python -m phase1.cli run -c config.yaml -v
```

### Initialize Configuration File

Generate a default configuration file:

```bash
# Activate venv first
source .venv/bin/activate

python -m phase1.cli init-config -o config.yaml
```

**Options:**
- `-o, --output`: Output config file path (default: `phase1_config.yaml`)
- `--format`: Config file format: `yaml` or `json` (default: `yaml`)

### Validate Output

Validate pipeline output:

```bash
# Activate venv first
source .venv/bin/activate

python -m phase1.cli validate workspace/
```

### Display Pipeline Information

Show pipeline information and usage:

```bash
# Activate venv first
source .venv/bin/activate

python -m phase1.cli info
```

### Interactive Selection Workflow

The interactive selection workflow combines human guidance with automation:

1. **User selects area visually** - Open QGIS, navigate to course, draw boundary
2. **Script extracts coordinates** - Automatically reads your selection
3. **Automated processing continues** - DEM merging, heightmaps, Unity conversion

This approach provides:
- Visual accuracy (see exactly what you're selecting)
- Flexibility (works with any coordinate system)
- User control (adjust selection before committing)
- Full automation (once selected, everything else is automated)

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
