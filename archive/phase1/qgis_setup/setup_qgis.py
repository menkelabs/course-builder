#!/usr/bin/env python3
"""
Main QGIS Setup Script

This script automates the complete QGIS setup process:
1. Installs QGIS (if not already installed)
2. Fixes Python path issues
3. Creates startup scripts
4. Verifies installation

Usage:
    python -m phase1.qgis_setup.setup_qgis
    # or
    python setup_qgis.py
"""

import sys
import os
import subprocess
from pathlib import Path

# Add parent directory to path so we can import other modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from qgis_setup.fix_qgis_python_v2 import create_enhanced_startup_script
from qgis_setup.test_qgis_startup import test_startup_script


def check_qgis_installed() -> bool:
    """Check if QGIS is installed."""
    try:
        result = subprocess.run(
            ["qgis", "--version"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def install_qgis() -> bool:
    """Install QGIS using the install script."""
    print("=" * 60)
    print("QGIS Installation")
    print("=" * 60)
    print("\nQGIS is not installed. Running installation script...")
    print("This requires sudo privileges.")
    print()
    
    install_script = Path(__file__).parent / "install_qgis.sh"
    if not install_script.exists():
        print(f"❌ Installation script not found: {install_script}")
        return False
    
    print(f"Running: sudo bash {install_script}")
    print("\nPlease enter your sudo password when prompted...")
    print()
    
    try:
        result = subprocess.run(
            ["sudo", "bash", str(install_script)],
            check=True
        )
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Installation failed: {e}")
        return False
    except KeyboardInterrupt:
        print("\n❌ Installation cancelled by user")
        return False


def fix_python_environment() -> bool:
    """Fix QGIS Python environment."""
    print("\n" + "=" * 60)
    print("Fixing QGIS Python Environment")
    print("=" * 60)
    print()
    
    try:
        startup_script = create_enhanced_startup_script()
        print(f"\n✓ Startup script created: {startup_script}")
        return True
    except Exception as e:
        print(f"❌ Failed to create startup script: {e}")
        return False


def verify_setup() -> bool:
    """Verify QGIS setup is working."""
    print("\n" + "=" * 60)
    print("Verifying Setup")
    print("=" * 60)
    print()
    
    try:
        success = test_startup_script()
        if success:
            print("\n✓ All tests passed!")
            return True
        else:
            print("\n⚠ Some tests failed, but setup may still work")
            return False
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False


def create_qgis_wrapper() -> bool:
    """Create QGIS wrapper script that sets PYTHONPATH."""
    print("\n" + "=" * 60)
    print("Creating QGIS Wrapper Script")
    print("=" * 60)
    print()
    
    wrapper_path = Path.home() / ".local" / "bin" / "qgis"
    wrapper_path.parent.mkdir(parents=True, exist_ok=True)
    
    wrapper_script = '''#!/bin/bash
# QGIS wrapper that sets PYTHONPATH before launching
export PYTHONPATH="/usr/lib/python3/dist-packages${PYTHONPATH:+:$PYTHONPATH}"
export QGIS_PREFIX_PATH="/usr"
exec /usr/bin/qgis "$@"
'''
    
    try:
        with open(wrapper_path, 'w') as f:
            f.write(wrapper_script)
        
        os.chmod(wrapper_path, 0o755)
        print(f"✓ Created QGIS wrapper: {wrapper_path}")
        print("  This ensures PYTHONPATH is set when QGIS launches")
        return True
    except Exception as e:
        print(f"⚠ Could not create wrapper: {e}")
        print("  This is optional - the startup script should still work")
        return False


def main():
    """Main setup function."""
    print("=" * 60)
    print("QGIS Setup for Phase 1")
    print("=" * 60)
    print()
    
    # Step 1: Check if QGIS is installed
    print("Step 1: Checking QGIS installation...")
    if not check_qgis_installed():
        print("❌ QGIS is not installed")
        response = input("\nWould you like to install QGIS now? (y/n): ").strip().lower()
        if response == 'y':
            if not install_qgis():
                print("\n❌ Setup failed during QGIS installation")
                return 1
        else:
            print("\n⚠ Skipping QGIS installation. Please install QGIS manually.")
            print("  See qgis_setup/QGIS_SETUP.md for instructions.")
            return 1
    else:
        print("✓ QGIS is installed")
    
    # Step 2: Fix Python environment
    print("\nStep 2: Fixing Python environment...")
    if not fix_python_environment():
        print("\n❌ Setup failed while fixing Python environment")
        return 1
    
    # Step 3: Create wrapper script
    print("\nStep 3: Creating QGIS wrapper script...")
    create_qgis_wrapper()  # Optional, don't fail if this doesn't work
    
    # Step 4: Verify setup
    print("\nStep 4: Verifying setup...")
    if not verify_setup():
        print("\n⚠ Verification had issues, but setup may still work")
        print("  Try opening QGIS and checking the Python console")
    
    # Success!
    print("\n" + "=" * 60)
    print("✓ QGIS Setup Complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Close QGIS if it's open")
    print("2. Restart QGIS")
    print("3. Open Python Console (Plugins -> Python Console)")
    print("4. You should see: '✓ QGIS Startup Script Executed Successfully!'")
    print()
    print("If you see any errors, see qgis_setup/QGIS_SIP_ERROR.md for troubleshooting")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
