"""
Standalone script to run boundary diagnostic using QGIS Python environment.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Setup QGIS environment
from phase1.pipeline.qgis_env import setup_qgis_environment
setup_qgis_environment()

# Import QGIS
from qgis.core import QgsApplication, QgsProject

# Initialize QGIS
QgsApplication.setPrefixPath('/usr', True)
qgs = QgsApplication([], False)
qgs.initQgis()

try:
    # Load the project
    project_path = project_root / "workspace_high_bridge" / "High Bridge_selection.qgz"
    
    if not project_path.exists():
        print(f"✗ Project file not found: {project_path}")
        sys.exit(1)
    
    project = QgsProject.instance()
    success = project.read(str(project_path))
    
    if not success:
        print(f"✗ Failed to load project: {project_path}")
        sys.exit(1)
    
    print(f"✓ Loaded project: {project_path}")
    
    # Run diagnostic
    exec(open(project_root / "phase1" / "pipeline" / "diagnose_boundary.py").read())
    
finally:
    qgs.exitQgis()
