# Phase 2A - Automated Satellite Tracing for Golf Courses

Convert satellite imagery of golf courses into structured SVG geometry using SAM (Segment Anything Model) for automatic feature extraction.

> **Note**: Phase 2A is one of several sections that will be developed as part of the complete course builder pipeline. See the [main README](../README.md) for an overview of all components and [plan.md](../plan.md) for the full automation specification.

## Features

- **Automatic Feature Extraction**: Uses SAM to generate candidate masks from satellite imagery
- **Multi-Image Support**: Combines features from multiple images of the same topography for better accuracy
- **Interactive Selection Workflow**: GUI-based hole-by-hole feature assignment with matplotlib visualization
- **Comprehensive Testing**: Unit tests, integration tests, and GUI tests (including resource image loading verification)
- **Feature Classification**: Classifies masks as water, bunker, green, fairway, rough, or ignore
- **SVG Generation**: Creates layered SVG output suitable for Unity, Blender, and GSPro

## Installation

1. Create a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies:
```bash
cd phase2a
pip install -e .
```

3. For GUI functionality (interactive selection):
```bash
pip install -e ".[gui]"
```

4. Download model checkpoints (see [Model Downloads](#model-downloads) section below).

## Model Downloads

Model files are large and not included in the repository. Download them to the `models/` directory at the project root.

### Create Models Directory

```bash
# From project root
mkdir -p models
cd models
```

### SAM (Segment Anything Model)

Choose ONE based on your GPU VRAM:

| Model | Size | VRAM Required | Quality |
|-------|------|---------------|---------|
| vit_h | 2.4 GB | 12+ GB | Best |
| vit_l | 1.2 GB | 8+ GB | Good |
| vit_b | 375 MB | 4+ GB | Faster |

```bash
# Option A: vit_h (recommended if you have 12GB+ VRAM)
wget https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth

# Option B: vit_l (good balance)
wget https://dl.fbaipublicfiles.com/segment_anything/sam_vit_l_0b3195.pth

# Option C: vit_b (fastest, lower quality)
wget https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth
```

### Grounding DINO (for auto-detect feature)

```bash
# Download Grounding DINO weights (~1.5 GB)
wget https://github.com/IDEA-Research/GroundingDINO/releases/download/v0.1.0-alpha/groundingdino_swint_ogc.pth

# Also install the Python package
pip install groundingdino-py
```

### Verify Downloads

```bash
# Your models directory should look like:
ls -la models/
# sam_vit_h_4b8939.pth      (2.4 GB)
# groundingdino_swint_ogc.pth (1.5 GB)
```

### Expected Directory Structure

```
course-builder/
├── models/                              # Model checkpoints (git-ignored)
│   ├── sam_vit_h_4b8939.pth            # SAM weights
│   └── groundingdino_swint_ogc.pth     # Grounding DINO weights
├── phase2a/
│   └── ...
└── ...
```

## Usage

### Auto-Detect with Grounding DINO (Recommended)

Automatically detect and segment golf course features using Grounding DINO + SAM:

```bash
phase2a auto-detect satellite.png \
    --dino-checkpoint models/groundingdino_swint_ogc.pth \
    --sam-checkpoint models/sam_vit_h_4b8939.pth \
    -o output/
```

**Options:**
- `--dino-checkpoint`: Grounding DINO model checkpoint (required)
- `--sam-checkpoint`: SAM model checkpoint (required)
- `--features`: Feature types to detect (default: green, fairway, bunker, tee)
- `--device`: Device to run on: `cuda` or `cpu` (default: `cuda`)
- `-o, --output`: Output directory (default: `phase2a_output`)

**Example with specific features:**
```bash
phase2a auto-detect satellite.png \
    --dino-checkpoint models/groundingdino_swint_ogc.pth \
    --sam-checkpoint models/sam_vit_h_4b8939.pth \
    --features green fairway bunker tee water \
    --device cuda \
    -o output/
```

This uses text prompts like "golf green", "sand bunker", etc. to automatically find features without manual clicking.

### Run Complete Pipeline

Run the full Phase 2A pipeline from satellite image to SVG:

```bash
phase2a run satellite.png --checkpoint models/sam_vit_h_4b8939.pth -o output/
```

**Options:**
- `-o, --output`: Output directory (default: `phase2a_output`)
- `-g, --green-centers`: JSON file with green center coordinates
- `-c, --config`: YAML or JSON configuration file
- `--checkpoint`: SAM model checkpoint path (required)
- `--device`: Device to run SAM on: `cuda` or `cpu` (default: `cuda`)
- `--high-threshold`: High confidence threshold for auto-accept (default: 0.85)
- `--low-threshold`: Low confidence threshold - below this masks are discarded (default: 0.5)
- `-v, --verbose`: Enable verbose output
- `--no-export-intermediates`: Skip saving intermediate outputs

**Example with options:**
```bash
phase2a run satellite.png \
  --checkpoint models/sam_vit_h_4b8939.pth \
  -o output/ \
  --device cuda \
  --high-threshold 0.9 \
  --low-threshold 0.4 \
  -v
```

### Interactive Selection Workflow

Interactive hole-by-hole feature assignment with GUI (point-based selection):

```bash
phase2a select satellite.png --checkpoint models/sam_vit_h_4b8939.pth -o output/
```

**Options:**
- `-o, --output`: Output directory (default: `phase2a_output`)
- `--checkpoint`: SAM model checkpoint path (required)
- `--selections`: Load existing selections JSON file
- `--model-type`: SAM model variant: `vit_h`, `vit_l`, or `vit_b` (default: `vit_h`)
- `--device`: Device to run SAM on: `cuda` or `cpu` (default: `cuda`)
- `-v, --verbose`: Enable verbose output

**This workflow:**
1. For each hole (1-18), prompts you to click on features
2. Uses SAM to automatically find the area around each click point
3. Assigns features: green, tee, fairway, and bunkers
4. Saves selections to `output/metadata/interactive_selections.json`
5. Extracts and saves green centers to `output/metadata/green_centers.json`

#### GUI Controls

- **Draw outline**: Click and drag to draw around a feature - SAM generates a mask
- **F key**: Toggle between SAM mode and Fill mode
  - **SAM mode** (default): SAM analyzes the outline and creates a mask based on color/texture
  - **Fill mode**: Draws a polygon that gets completely filled (no SAM processing)
- **M key**: Merge all selected masks into one with smooth edges
- **Enter/Space**: Confirm selection for current feature type
- **Esc**: Undo last mask generation
- **Scroll wheel**: Zoom in/out
- **Done button**: Confirm and move to next feature type

The workflow repeats for each hole until all 18 holes are assigned.

### Mask Completion Workflow

When SAM doesn't fully capture an area due to inconsistent shading:

1. **Draw with SAM mode** (default): Draw around the feature - SAM generates a partial mask
2. **Press F** to switch to **Fill mode**
3. **Draw the missing area**: Draw a polygon covering the part SAM missed - it fills completely
4. **Press M** to **merge** both masks into one with smooth edges
5. Continue to the next feature

This workflow ensures complete coverage while maintaining smooth, natural-looking boundaries.

### Visual Workflow Guide

The interactive selection workflow guides you through assigning features to each hole step-by-step. Watch the video below for a complete walkthrough:

<div align="center">
  <a href="https://www.youtube.com/watch?v=ErSb4hcTAe4">
    <img src="https://img.youtube.com/vi/ErSb4hcTAe4/maxresdefault.jpg" alt="Phase 2A Workflow Video" style="width:100%;max-width:800px;">
  </a>
  <br>
  <a href="https://www.youtube.com/watch?v=ErSb4hcTAe4">Watch on YouTube: Phase 2A Interactive Workflow</a>
</div>

### Generate Masks Only

Generate SAM masks from an image without running the full pipeline:

```bash
phase2a generate-masks image.png --checkpoint models/sam_vit_h_4b8939.pth -o masks/
```

**Options:**
- `-o, --output`: Output directory for masks (default: `masks`)
- `--checkpoint`: SAM model checkpoint path (required)
- `--model-type`: SAM model variant: `vit_h`, `vit_l`, or `vit_b` (default: `vit_h`)
- `--points-per-side`: Points per side for grid sampling (default: 32)
- `-v, --verbose`: Enable verbose output

### Export SVG to PNG

Export an SVG file to PNG overlay:

```bash
phase2a export-png course.svg -o overlay.png
```

**Options:**
- `-o, --output`: Output PNG path (default: same name as SVG with .png extension)
- `-w, --width`: Output width (default: from SVG)
- `-h, --height`: Output height (default: from SVG)
- `-v, --verbose`: Enable verbose output

### Initialize Configuration File

Generate a default configuration file:

```bash
phase2a init-config -o config.yaml
```

**Options:**
- `-o, --output`: Output config file path (default: `phase2a_config.yaml`)
- `--format`: Config file format: `yaml` or `json` (default: `yaml`)

### Validate Output

Validate pipeline output (svg_complete gate):

```bash
phase2a validate output/
```

Checks for:
- SVG file existence
- PNG overlay existence
- Classifications with required feature types (water, bunkers, greens)

### Display Pipeline Information

Show pipeline information and usage:

```bash
phase2a info
```

## Testing

Run all tests:
```bash
cd phase2a
pytest
```

Run with GUI tests (requires Qt5Agg or TkAgg backend):
```bash
pytest -m gui
```

Run tests excluding slow tests:
```bash
pytest -m "not slow"
```

The test suite includes:
- Unit tests for individual pipeline components
- Integration tests with resource images (Pictatinny_B.jpg, Pictatinny_G.jpg)
- GUI integration tests that verify matplotlib window creation and image display
- Tests that verify actual resource images load and display correctly

## Project Structure

```
phase2a/
├── pipeline/          # Core pipeline modules
│   ├── masks.py      # SAM mask generation
│   ├── features.py   # Feature extraction (with multi-image support)
│   ├── classify.py   # Mask classification
│   ├── gating.py     # Confidence-based gating
│   ├── polygons.py   # Polygon generation
│   ├── svg.py        # SVG generation
│   ├── export.py     # PNG export
│   ├── interactive.py # Interactive selection logic
│   └── visualize.py  # Matplotlib visualization
├── tests/            # Test suite
│   ├── test_*.py     # Unit and integration tests
│   └── test_gui_integration.py  # GUI tests
├── resources/        # Test images (Pictatinny_B.jpg, Pictatinny_G.jpg)
└── cli.py           # Command-line interface
```

## Configuration

The pipeline can be configured via:
- CLI options (see `phase2a run --help`)
- YAML/JSON config files (use `--config` option)
- `Phase2AConfig` class in `phase2a/config.py`

Key configuration options:
- SAM checkpoint path
- Confidence thresholds (high/low)
- Green centers file (`green_centers.json`)
- Multi-image input (for improved accuracy)

## Output Structure

```
phase2a_output/
├── satellite_normalized.png
├── masks/                    # Generated masks
├── polygons/                 # Vector polygons
├── reviews/                  # Masks requiring review
├── metadata/
│   ├── mask_features.json
│   ├── classifications.json
│   ├── hole_assignments.json
│   └── interactive_selections.json  # From interactive workflow
├── course.svg                # Final SVG output
└── exports/
    └── overlay.png           # Rendered overlay
```

## Development

The project uses:
- **Python 3.10+**
- **pytest** for testing
- **matplotlib** for GUI visualization (optional)
- **Click** for CLI
- **Rich** for console output

See [../phase2a.md](../phase2a.md) for detailed design specification.
