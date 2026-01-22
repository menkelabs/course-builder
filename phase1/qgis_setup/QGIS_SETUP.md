# QGIS Installation Guide

This guide covers installing QGIS on Ubuntu/Debian systems for use with Phase 1 terrain preparation.

## Prerequisites

- Ubuntu 20.04+ or Debian 11+
- sudo/root access
- Internet connection

## Installation Steps

### Quick Install (Recommended)

**Option 1: Automated Setup (Recommended)**

Run the complete automated setup:

```bash
# From project root
source .venv/bin/activate
python -m phase1.qgis_setup.setup_qgis
```

This will:
1. Install QGIS (if needed)
2. Fix Python path issues
3. Create startup scripts
4. Verify everything works

**Option 2: Manual Installation**

Use the provided installation script:

```bash
cd phase1/qgis_setup
sudo bash install_qgis.sh
```

This script will:
1. Update system packages
2. Add QGIS repository key
3. Configure QGIS repository
4. Install QGIS and GRASS plugin
5. Verify the installation

### Manual Installation

If you prefer to install manually:

#### 1. Update System Packages

```bash
sudo apt update
sudo apt install ca-certificates gnupg lsb-release software-properties-common
```

#### 2. Add QGIS Repository Key

```bash
sudo mkdir -p /etc/apt/keyrings
sudo wget -O /etc/apt/keyrings/qgis-archive-keyring.gpg https://download.qgis.org/downloads/qgis-archive-keyring.gpg
```

#### 3. Add QGIS Repository

```bash
echo \
"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/qgis-archive-keyring.gpg] https://qgis.org/ubuntu-ltr \
$(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/qgis.list > /dev/null
```

#### 4. Update Package Lists

```bash
sudo apt update
```

#### 5. Install QGIS

Install QGIS Desktop (includes GUI and CLI tools):

```bash
sudo apt install qgis qgis-plugin-grass
```

Or install only the CLI tools (for headless servers):

```bash
sudo apt install qgis-server qgis-processing
```

### 6. Verify Installation

Check that `qgis_process` is available:

```bash
qgis_process --version
```

You should see output like:
```
QGIS Processing version 3.x.x
```

List available algorithms:

```bash
qgis_process list
```

## Configuration

### Finding qgis_process Path

If `qgis_process` is not in your PATH, find it:

```bash
which qgis_process
# or
find /usr -name qgis_process 2>/dev/null
```

Common locations:
- `/usr/bin/qgis_process`
- `/usr/lib/qgis/bin/qgis_process`

### Python Bindings Setup

QGIS Python bindings require environment variables to be set. Use the provided setup script:

```bash
cd phase1
source setup_qgis_env.sh
```

Or set manually:

```bash
export QGIS_PREFIX_PATH="/usr"
export PYTHONPATH="/usr/share/qgis/python:$PYTHONPATH"
export LD_LIBRARY_PATH="/usr/lib/qgis:$LD_LIBRARY_PATH"
```

**Important**: You must set these environment variables before importing QGIS in Python scripts.

To make this permanent, add to your `~/.bashrc` or `~/.zshrc`:

```bash
# QGIS Python Environment
export QGIS_PREFIX_PATH="/usr"
export PYTHONPATH="/usr/share/qgis/python:$PYTHONPATH"
export LD_LIBRARY_PATH="/usr/lib/qgis:$LD_LIBRARY_PATH"
```

Then test:

```bash
python3 -c "from qgis.core import QgsApplication; print('QGIS Python bindings OK')"
```

## Testing QGIS

### Test Basic Algorithm

Test that QGIS processing works:

```bash
qgis_process run native:buffer \
  --INPUT="type=point" \
  --DISTANCE=100 \
  --OUTPUT=/tmp/test_buffer.shp
```

### Test with Python

Create a test script `test_qgis.py`:

```python
# Use the Phase 1 QGIS environment helper
from pipeline.qgis_env import setup_qgis_environment
setup_qgis_environment()

from qgis.core import QgsApplication
import sys

# Initialize QGIS
QgsApplication.setPrefixPath('/usr', True)
qgs = QgsApplication([], False)
qgs.initQgis()

# Test processing
from qgis import processing
algorithms = processing.algorithmHelp("native:buffer")
print("QGIS Processing is working!")

qgs.exitQgis()
```

Run it:

```bash
python3 test_qgis.py
```

**Note**: Always import `pipeline.qgis_env` before importing any QGIS modules in Phase 1 scripts.

## Troubleshooting

### "Couldn't load SIP module" or "ModuleNotFoundError: No module named 'qgis'"

This error occurs when QGIS Python bindings can't find the required modules. Fix it by:

1. **Use the environment setup script** (recommended):
   ```bash
   source phase1/setup_qgis_env.sh
   ```

2. **Or use the Python helper module** in your scripts:
   ```python
   from pipeline.qgis_env import setup_qgis_environment
   setup_qgis_environment()
   from qgis.core import QgsApplication
   ```

3. **Or set environment variables manually**:
   ```bash
   export QGIS_PREFIX_PATH="/usr"
   export PYTHONPATH="/usr/share/qgis/python:$PYTHONPATH"
   export LD_LIBRARY_PATH="/usr/lib/qgis:$LD_LIBRARY_PATH"
   ```

4. **Verify Python QGIS package is installed**:
   ```bash
   dpkg -l | grep python3-qgis
   ```
   If not installed: `sudo apt install python3-qgis`

### qgis_process not found

If `qgis_process` command is not found:

1. Check if QGIS is installed:
   ```bash
   dpkg -l | grep qgis
   ```

2. Add QGIS bin to PATH:
   ```bash
   export PATH=/usr/lib/qgis/bin:$PATH
   ```

3. Create a symlink:
   ```bash
   sudo ln -s /usr/lib/qgis/bin/qgis_process /usr/local/bin/qgis_process
   ```

### Permission Issues

If you get permission errors:

```bash
sudo chmod +x /usr/lib/qgis/bin/qgis_process
```

### "Couldn't load SIP module" Error in QGIS Console

If you see this error when opening QGIS:

```
Couldn't load SIP module.
Python support will be disabled.
ModuleNotFoundError: No module named 'qgis'
```

**Fix:** Run the QGIS setup script:

```bash
# From project root
source .venv/bin/activate
python -m phase1.qgis_setup.setup_qgis
```

Or manually fix the Python path:

```bash
cd phase1/qgis_setup
source ../../.venv/bin/activate
python fix_qgis_python_v2.py
```

This creates a QGIS startup script that adds `/usr/lib/python3/dist-packages` to the Python path.

**After running the fix:**
1. Close QGIS if it's open
2. Restart QGIS
3. The error should be gone!

**To verify:** Open QGIS Python console (Plugins -> Python Console) and type:
```python
import qgis.core
```

It should work without errors.

**Note:** This error doesn't affect QGIS GUI functionality or our Phase 1 scripts. It only affects QGIS's built-in Python console. However, fixing it ensures full QGIS functionality.

### Python Import Errors (for external scripts)

If Python can't import QGIS modules in external scripts (not QGIS GUI):

1. Install Python QGIS bindings:
   ```bash
   sudo apt install python3-qgis
   ```

2. Phase 1 scripts automatically configure the environment via `phase1/pipeline/qgis_env.py`.
   No manual configuration needed!

## Phase 1 Configuration

Once QGIS is installed, configure Phase 1 to use it:

### Option 1: Auto-detect (Recommended)

Phase 1 will automatically find `qgis_process` if it's in your PATH.

### Option 2: Manual Configuration

Create or edit `phase1_config.yaml`:

```yaml
qgis:
  qgis_process_path: "/usr/bin/qgis_process"  # or actual path
  default_crs: "EPSG:3857"
```

## Additional Resources

- [QGIS Official Documentation](https://qgis.org/documentation/)
- [QGIS Processing Framework](https://docs.qgis.org/latest/en/docs/user_manual/processing/index.html)
- [QGIS Python API](https://qgis.org/pyqgis/master/)

## Post-Installation Setup

After QGIS is installed, **fix the Python console** (recommended):

```bash
# From project root
source .venv/bin/activate
python -m phase1.qgis_setup.setup_qgis
```

This fixes the "Couldn't load SIP module" error in QGIS's Python console.

## Next Steps

After QGIS is installed and configured:

1. Verify installation: `qgis_process --version`
2. Fix Python console: `python -m phase1.qgis_setup.setup_qgis` (see above)
3. Test with Phase 1: `python -m phase1.cli info` (after activating root .venv)
4. Run a test pipeline: `python -m phase1.cli run --course-name TestCourse -o test_workspace/`
