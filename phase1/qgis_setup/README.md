# QGIS Setup Package

This package contains all scripts and documentation needed to set up QGIS for Phase 1 of the course builder.

## Quick Start

Run the automated setup script:

```bash
# From project root
source .venv/bin/activate
python -m phase1.qgis_setup.setup_qgis
```

Or run directly:

```bash
cd phase1/qgis_setup
python setup_qgis.py
```

## What This Package Does

1. **Installs QGIS** (if not already installed)
2. **Fixes Python path issues** - Creates startup script that adds `/usr/lib/python3/dist-packages` to Python path
3. **Creates QGIS wrapper** - Ensures PYTHONPATH is set when QGIS launches
4. **Verifies setup** - Tests that everything works

## Files in This Package

### Setup Scripts

- **`setup_qgis.py`** - Main automated setup script (run this first!)
- **`install_qgis.sh`** - Installs QGIS on Ubuntu/Debian systems
- **`fix_qgis_python_v2.py`** - Creates QGIS startup script to fix Python path
- **`test_qgis_startup.py`** - Tests that the startup script works

### Documentation

- **`QGIS_SETUP.md`** - Complete QGIS installation and setup guide
- **`QGIS_SIP_ERROR.md`** - Troubleshooting guide for SIP errors
- **`DEBUG_QGIS.md`** - Advanced debugging guide
- **`DEBUG_RESULTS.md`** - Debug test results reference

## Manual Setup

If you prefer to set up manually:

1. **Install QGIS:**
   ```bash
   sudo bash qgis_setup/install_qgis.sh
   ```

2. **Fix Python environment:**
   ```bash
   python qgis_setup/fix_qgis_python_v2.py
   ```

3. **Verify setup:**
   ```bash
   python qgis_setup/test_qgis_startup.py
   ```

## Troubleshooting

If you encounter issues:

1. See `QGIS_SIP_ERROR.md` for common SIP errors
2. See `DEBUG_QGIS.md` for advanced debugging
3. Run `test_qgis_startup.py` to diagnose issues

## Integration with Phase 1

Once QGIS is set up, Phase 1 will automatically:
- Use the QGIS wrapper script (if available)
- Set PYTHONPATH when launching QGIS
- Work with the startup script to ensure Python bindings are available

No additional configuration needed!
