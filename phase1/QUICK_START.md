# Phase 1 Quick Start Guide

## Prerequisites

- Python 3.9+ installed
- QGIS installed (see [qgis_setup/QGIS_SETUP.md](qgis_setup/QGIS_SETUP.md) or run `python -m phase1.qgis_setup.setup_qgis`)
- Virtual environment at project root

## Setup (One-Time)

### 1. Activate Root Virtual Environment

The project uses a shared `.venv` at the **project root**, not in `phase1/`:

```bash
# From project root
cd /path/to/course-builder
source .venv/bin/activate
```

### 2. Install Phase 1

```bash
cd phase1
pip install -e .
```

**Or use the setup script:**
```bash
# From project root
bash phase1/setup_venv.sh
```

### 3. Verify Installation

```bash
python -m phase1.cli --help
```

## Usage

### Interactive Course Selection

**Step 1: Activate virtual environment**
```bash
cd /path/to/course-builder
source .venv/bin/activate
```

**Step 2: Launch interactive selection**
```bash
python -m phase1.cli interactive-select --course-name "Pine Valley" -o workspace/
```

This will:
1. Open QGIS with satellite imagery
2. Wait for you to draw a polygon around the golf course
3. Automatically extract coordinates when you save
4. Save bounds to `workspace/course_bounds.json`

### Full Pipeline

```bash
# Activate venv first
source .venv/bin/activate

# Run full pipeline (will launch interactive selection if no bounds exist)
python -m phase1.cli run --course-name "Pine Valley" -o workspace/
```

## Making phase1 a Command (Optional)

If you want to use `phase1` directly instead of `python -m phase1.cli`:

```bash
# Activate venv
source .venv/bin/activate

# Install phase1
cd phase1
pip install -e .

# Now you can use:
phase1 interactive-select --course-name "Pine Valley" -o workspace/
phase1 run --course-name "Pine Valley" -o workspace/
```

## Important Notes

- **Always activate the root `.venv`** before running Phase 1 commands
- The `.venv` is at `course-builder/.venv`, not `course-builder/phase1/.venv`
- If you get "ModuleNotFoundError", make sure you've activated the venv and installed phase1

## Troubleshooting

### "ModuleNotFoundError: No module named 'phase1'"

**Solution:**
```bash
# Make sure you're in the project root
cd /path/to/course-builder

# Activate the venv
source .venv/bin/activate

# Install phase1
cd phase1
pip install -e .
```

### "qgis_process not found"

**Solution:** Install QGIS (see [qgis_setup/QGIS_SETUP.md](qgis_setup/QGIS_SETUP.md) or run `python -m phase1.qgis_setup.setup_qgis`)

### "Couldn't load SIP module" in QGIS Console

**Solution:** Run QGIS setup:
```bash
source .venv/bin/activate
python -m phase1.qgis_setup.setup_qgis
```

Then restart QGIS. This fixes the error in QGIS's Python console.

**Note:** This error doesn't affect Phase 1 scripts or QGIS GUI functionality. It only affects QGIS's built-in Python console.
