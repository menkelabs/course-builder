#!/bin/bash
# QGIS Python Environment Setup Script
# Source this file to configure QGIS Python bindings: source setup_qgis_env.sh

# Find QGIS installation
QGIS_PREFIX="/usr"
QGIS_PYTHON_PATH="/usr/share/qgis/python"
QGIS_LIB_PATH="/usr/lib/qgis"

# Check if paths exist
if [ ! -d "$QGIS_PYTHON_PATH" ]; then
    echo "Warning: QGIS Python path not found at $QGIS_PYTHON_PATH"
fi

if [ ! -d "$QGIS_LIB_PATH" ]; then
    echo "Warning: QGIS lib path not found at $QGIS_LIB_PATH"
fi

# Export environment variables
export QGIS_PREFIX_PATH="$QGIS_PREFIX"
export PYTHONPATH="$QGIS_PYTHON_PATH:$PYTHONPATH"
export LD_LIBRARY_PATH="$QGIS_LIB_PATH:$LD_LIBRARY_PATH"
export QT_QPA_PLATFORM_PLUGIN_PATH="$QGIS_PREFIX/lib/qt5/plugins"

echo "QGIS environment configured:"
echo "  QGIS_PREFIX_PATH=$QGIS_PREFIX_PATH"
echo "  PYTHONPATH includes: $QGIS_PYTHON_PATH"
echo "  LD_LIBRARY_PATH includes: $QGIS_LIB_PATH"

# Test import
python3 << EOF
import sys
sys.path.insert(0, "$QGIS_PYTHON_PATH")
try:
    from qgis.core import QgsApplication
    print("✓ QGIS Python bindings loaded successfully!")
except ImportError as e:
    print(f"✗ Failed to import QGIS: {e}")
    sys.exit(1)
EOF
