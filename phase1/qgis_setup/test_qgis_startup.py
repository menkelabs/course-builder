#!/usr/bin/env python3
"""
Test if QGIS startup script is working.

This script simulates what QGIS does when it starts and checks if
the startup script would work.
"""

import sys
import os
from pathlib import Path

def test_startup_script():
    """Test the QGIS startup script logic."""
    print("Testing QGIS startup script logic...")
    print("=" * 60)
    
    # Simulate QGIS's initial Python path (from the error message)
    qgis_python_path = [
        '/usr/share/qgis/python',
        '/home/ubuntu/.local/share/QGIS/QGIS3/profiles/default/python',
        '/home/ubuntu/.local/share/QGIS/QGIS3/profiles/default/python/plugins',
        '/usr/share/qgis/python/plugins',
        '/usr/lib/python310.zip',
        '/usr/lib/python3.10',
        '/usr/lib/python3.10/lib-dynload',
        '/home/ubuntu/github/jmjava/course-builder/.venv/lib/python3.10/site-packages'
    ]
    
    print("\n1. Initial Python path (as QGIS sees it):")
    for p in qgis_python_path:
        print(f"   {p}")
    
    # Check if dist-packages is missing
    dist_packages = "/usr/lib/python3/dist-packages"
    if dist_packages not in qgis_python_path:
        print(f"\n❌ {dist_packages} is NOT in the path!")
    else:
        print(f"\n✓ {dist_packages} is in the path")
    
    # Apply startup script logic
    print("\n2. Applying startup script fix...")
    if dist_packages not in sys.path:
        sys.path.insert(0, dist_packages)
        print(f"   ✓ Added {dist_packages} to sys.path")
    else:
        print(f"   ✓ {dist_packages} already in sys.path")
    
    # Try importing PyQt5.sip
    print("\n3. Testing PyQt5.sip import...")
    try:
        import PyQt5.sip
        print("   ✓ PyQt5.sip imported successfully")
    except ImportError as e:
        print(f"   ❌ Failed to import PyQt5.sip: {e}")
        # Try to find PyQt5
        pyqt5_path = os.path.join(dist_packages, "PyQt5")
        if os.path.exists(pyqt5_path):
            print(f"   Trying to add {pyqt5_path} to path...")
            if pyqt5_path not in sys.path:
                sys.path.insert(0, pyqt5_path)
            try:
                import PyQt5.sip
                print("   ✓ PyQt5.sip imported after path fix")
            except ImportError as e2:
                print(f"   ❌ Still failed: {e2}")
    
    # Try importing qgis.core
    print("\n4. Testing qgis.core import...")
    try:
        import qgis.core
        print("   ✓ qgis.core imported successfully!")
        print(f"   QGIS version: {qgis.core.Qgis.QGIS_VERSION}")
        return True
    except ImportError as e:
        print(f"   ❌ Failed to import qgis.core: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Error importing qgis.core: {e}")
        return False

def check_startup_script_location():
    """Check if startup script is in the right place."""
    print("\n" + "=" * 60)
    print("Checking startup script location...")
    
    startup_path = Path.home() / ".local" / "share" / "QGIS" / "QGIS3" / "profiles" / "default" / "python" / "startup.py"
    
    if startup_path.exists():
        print(f"✓ Startup script exists: {startup_path}")
        print(f"  Size: {startup_path.stat().st_size} bytes")
        
        # Check if it's readable
        try:
            content = startup_path.read_text()
            if "dist_packages" in content:
                print("  ✓ Contains dist_packages fix")
            if "PyQt5.sip" in content:
                print("  ✓ Contains PyQt5.sip import")
            if "qgis.core" in content:
                print("  ✓ Contains qgis.core import test")
        except Exception as e:
            print(f"  ❌ Error reading script: {e}")
    else:
        print(f"❌ Startup script NOT found: {startup_path}")
        print("  Run: python fix_qgis_python.py")

def check_qgis_profiles():
    """Check for other QGIS profiles."""
    print("\n" + "=" * 60)
    print("Checking for QGIS profiles...")
    
    profiles_dir = Path.home() / ".local" / "share" / "QGIS" / "QGIS3" / "profiles"
    if profiles_dir.exists():
        profiles = list(profiles_dir.iterdir())
        print(f"Found {len(profiles)} profile(s):")
        for profile in profiles:
            if profile.is_dir():
                startup = profile / "python" / "startup.py"
                if startup.exists():
                    print(f"  ✓ {profile.name}: startup.py exists")
                else:
                    print(f"  - {profile.name}: no startup.py")
    else:
        print("No QGIS profiles directory found")

if __name__ == "__main__":
    print("QGIS Startup Script Diagnostic")
    print("=" * 60)
    
    check_startup_script_location()
    check_qgis_profiles()
    
    success = test_startup_script()
    
    print("\n" + "=" * 60)
    if success:
        print("✓ All tests passed! The startup script should work.")
        print("\nIf QGIS still shows the error:")
        print("1. Make sure QGIS is completely closed")
        print("2. Check QGIS logs for startup script errors")
        print("3. Try creating a new QGIS profile")
    else:
        print("❌ Some tests failed. The startup script may not work.")
        print("\nTroubleshooting:")
        print("1. Check if python3-qgis is installed: dpkg -l | grep python3-qgis")
        print("2. Check if /usr/lib/python3/dist-packages/qgis exists")
        print("3. Try running: python fix_qgis_python.py again")
