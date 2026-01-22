"""
Allow running setup_qgis as a module: python -m phase1.qgis_setup
"""

from .setup_qgis import main
import sys

if __name__ == "__main__":
    sys.exit(main())
