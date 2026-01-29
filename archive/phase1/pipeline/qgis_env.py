"""
QGIS Environment Setup

Automatically configures QGIS Python environment when imported.
This module should be imported before any QGIS imports.
"""

import os
import sys
from pathlib import Path


def setup_qgis_environment():
    """
    Configure QGIS Python environment variables.
    
    This function sets up the necessary environment variables for QGIS
    Python bindings to work correctly. It should be called before
    importing any QGIS modules.
    
    Critical: QGIS requires PyQt5.sip to be available and system dist-packages
    to be in the path for the qgis module.
    """
    # Default QGIS installation paths (Ubuntu/Debian)
    qgis_prefix = os.environ.get("QGIS_PREFIX_PATH", "/usr")
    qgis_python_path = os.environ.get("QGIS_PYTHON_PATH", "/usr/share/qgis/python")
    qgis_lib_path = os.environ.get("QGIS_LIB_PATH", "/usr/lib/qgis")
    qgis_dist_packages = "/usr/lib/python3/dist-packages"  # QGIS Python bindings location
    
    # CRITICAL: Add dist-packages FIRST and ensure it stays first
    # This is where QGIS Python bindings are installed
    # Remove it first if it exists elsewhere in path, then add at beginning
    if qgis_dist_packages in sys.path:
        sys.path.remove(qgis_dist_packages)
    if os.path.exists(qgis_dist_packages):
        sys.path.insert(0, qgis_dist_packages)
    
    # Add QGIS Python path (plugins, etc.) - but after dist-packages
    if qgis_python_path in sys.path:
        sys.path.remove(qgis_python_path)
    if os.path.exists(qgis_python_path):
        # Insert after dist-packages (index 1)
        if len(sys.path) > 0 and sys.path[0] == qgis_dist_packages:
            sys.path.insert(1, qgis_python_path)
        else:
            sys.path.insert(0, qgis_python_path)
    
    # Ensure PyQt5.sip is available (QGIS requires this)
    # Import PyQt5.sip BEFORE importing qgis - this is critical!
    try:
        import PyQt5.sip
        # Verify it worked
        if not hasattr(PyQt5.sip, 'unwrapinstance'):
            raise ImportError("PyQt5.sip is not properly initialized")
    except ImportError as e:
        # This is a critical failure - QGIS won't work without SIP
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to import PyQt5.sip: {e}")
        logger.error("QGIS Python bindings require PyQt5.sip to be available")
        logger.error("Make sure PyQt5 is installed: pip install PyQt5")
        raise
    
    # Set environment variables
    os.environ["QGIS_PREFIX_PATH"] = qgis_prefix
    
    # Update LD_LIBRARY_PATH
    current_ld_path = os.environ.get("LD_LIBRARY_PATH", "")
    if qgis_lib_path not in current_ld_path and os.path.exists(qgis_lib_path):
        os.environ["LD_LIBRARY_PATH"] = f"{qgis_lib_path}:{current_ld_path}" if current_ld_path else qgis_lib_path
    
    # Set QT plugin path if it exists
    qt_plugin_path = f"{qgis_prefix}/lib/qt5/plugins"
    if os.path.exists(qt_plugin_path):
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = qt_plugin_path


def verify_qgis_import():
    """
    Verify that QGIS can be imported.
    
    Returns:
        bool: True if QGIS can be imported, False otherwise
    """
    try:
        setup_qgis_environment()
        from qgis.core import QgsApplication
        return True
    except ImportError:
        return False


# Auto-setup when module is imported
setup_qgis_environment()
