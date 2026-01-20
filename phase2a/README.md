# course-builder

Phase 2A - Automated Satellite Tracing for Golf Courses

Convert satellite imagery of golf courses into structured SVG geometry using SAM (Segment Anything Model) for automatic feature extraction.

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

4. Download SAM checkpoint (e.g., `sam_vit_h_4b8939.pth`) to `checkpoints/` directory.

## Usage

### Run Complete Pipeline

```bash
phase2a run satellite.png --checkpoint checkpoints/sam_vit_h_4b8939.pth -o output/
```

### Interactive Selection Workflow

For hole-by-hole feature assignment with GUI:

```bash
phase2a select satellite.png --checkpoint checkpoints/sam_vit_h_4b8939.pth -o output/
```

This workflow:
1. Generates candidate masks using SAM
2. Opens an interactive GUI window for each hole (1-18)
3. Prompts you to click on masks for: green, tee, fairway, and bunkers
4. Saves selections to `output/metadata/interactive_selections.json`

### Visual Workflow Guide

The interactive selection workflow guides you through assigning features to each hole step-by-step. Watch the video below for a complete walkthrough:

<div align="center">
  <a href="https://www.youtube.com/watch?v=ErSb4hcTAe4">
    <img src="https://img.youtube.com/vi/ErSb4hcTAe4/maxresdefault.jpg" alt="Phase 2A Workflow Video" style="width:100%;max-width:800px;">
  </a>
  <br>
  <a href="https://www.youtube.com/watch?v=ErSb4hcTAe4">Watch on YouTube: Phase 2A Interactive Workflow</a>
</div>

#### GUI Controls

- **Click on mask**: Toggle selection (selected = red highlight)
- **Enter/Space**: Confirm selection for current feature type
- **Esc**: Clear current selection
- **Done button**: Confirm and move to next feature type

The workflow repeats for each hole until all 18 holes are assigned.

### Generate Masks Only

```bash
phase2a generate-masks image.png --checkpoint checkpoints/sam_vit_h_4b8939.pth -o masks/
```

### Other Commands

```bash
phase2a info              # Display pipeline information
phase2a validate output/  # Validate output directory
phase2a export-png svg    # Export SVG to PNG overlay
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

See `phase2a.md` for detailed design specification.
