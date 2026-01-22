# QGIS SIP Error - Understanding and Workaround

## The Error

When opening QGIS, you may see this error in the Python console:

```
Couldn't load SIP module.
Python support will be disabled.

Traceback (most recent call last):
  File "", line 1, in 
ModuleNotFoundError: No module named 'qgis'
```

## What This Means

**This error is from QGIS GUI's Python console, NOT from our Phase 1 script.**

The error occurs because:
1. QGIS GUI uses its own Python environment
2. That environment doesn't include `/usr/lib/python3/dist-packages` in the path
3. QGIS Python bindings are installed in `/usr/lib/python3/dist-packages/qgis`
4. Without that path, QGIS GUI's Python console can't find the `qgis` module

## Important: This Does NOT Break the Workflow!

**The QGIS GUI itself works perfectly fine!** You can still:
- ✅ Open QGIS
- ✅ Navigate to locations
- ✅ Draw polygons
- ✅ Save shapefiles
- ✅ Use all QGIS features

The error only affects QGIS's **Python console** (Plugins -> Python Console), which we don't need for the interactive selection workflow.

## Our Script Works Fine

Our Phase 1 script uses QGIS Python bindings correctly:
- ✅ Template creation works
- ✅ QGIS launches successfully
- ✅ Boundary extraction from shapefiles works

The script runs in the **root .venv** which has proper QGIS bindings configured.

## Workflow

The interactive selection workflow works like this:

1. **Our script** (runs in .venv with proper QGIS bindings):
   - Creates QGIS template ✅
   - Launches QGIS GUI ✅

2. **You use QGIS GUI** (works fine, ignore SIP error):
   - Navigate to golf course ✅
   - Draw polygon boundary ✅
   - Save as shapefile ✅

3. **Our script** (continues automatically):
   - Detects saved shapefile ✅
   - Extracts coordinates ✅
   - Saves bounds JSON ✅

## If You Need QGIS Python Console

If you want to use QGIS's Python console (optional), you can fix it by:

### Option 1: Add dist-packages to QGIS Python path

Create/edit `~/.local/share/QGIS/QGIS3/profiles/default/python/startup.py`:

```python
import sys
sys.path.insert(0, '/usr/lib/python3/dist-packages')
```

### Option 2: Use system Python for QGIS

Run QGIS with system Python instead of venv Python (not recommended, but works).

## Summary

- **SIP error in QGIS console**: Harmless, doesn't affect GUI usage
- **Our script**: Works correctly with QGIS bindings
- **Workflow**: Fully functional - draw boundary, save shapefile, script continues
- **Action needed**: None! Just ignore the SIP error and use QGIS GUI normally

## Verification

To verify everything works:

```bash
# Activate venv
source .venv/bin/activate

# Run interactive selection
python -m phase1.cli interactive-select --course-name "Test" -o test_workspace/ -v

# You'll see:
# ✓ Template created
# ✓ QGIS launched
# (SIP error may appear in QGIS - ignore it)
# Draw boundary in QGIS GUI
# Save as shapefile
# ✓ Script detects and extracts bounds
```

The SIP error is cosmetic and doesn't prevent the workflow from working!
