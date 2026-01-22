# WSL2 Setup Guide for SAM + Grounding DINO

This guide walks through setting up WSL2 on Windows to run SAM (Segment Anything Model) and Grounding DINO with GPU acceleration.

## Prerequisites

- Windows 10 (version 2004+) or Windows 11
- NVIDIA GPU with CUDA support (GTX 10xx series or newer)
- At least 16GB RAM recommended
- At least 50GB free disk space

## Step 1: Install/Update NVIDIA Windows Driver

**Critical**: Install the latest NVIDIA driver on **Windows** (not inside WSL).

1. Download from [NVIDIA Driver Downloads](https://www.nvidia.com/Download/index.aspx)
2. Select your GPU model and Windows version
3. Install and reboot

Verify the driver version is 470.76 or newer (required for WSL2 CUDA):
```powershell
nvidia-smi
```

## Step 2: Enable WSL2

Open PowerShell as Administrator:

```powershell
# Enable WSL
wsl --install

# Set WSL2 as default
wsl --set-default-version 2

# Reboot if prompted
```

After reboot, install Ubuntu:

```powershell
# Install Ubuntu 22.04 (recommended for CUDA compatibility)
wsl --install -d Ubuntu-22.04
```

Set up your Linux username and password when prompted.

## Step 3: Configure WSL2 Memory (Optional but Recommended)

Create/edit `%UserProfile%\.wslconfig` in Windows:

```ini
[wsl2]
memory=12GB
processors=4
swap=8GB
```

Restart WSL:
```powershell
wsl --shutdown
```

## Step 4: Verify GPU Access in WSL2

Open your Ubuntu WSL terminal:

```bash
# Check if NVIDIA GPU is visible
nvidia-smi
```

You should see your GPU listed. If not, ensure:
- Windows NVIDIA driver is up to date
- WSL2 is properly installed (not WSL1)

## Step 5: Install CUDA Toolkit in WSL2

**Important**: Do NOT install NVIDIA drivers inside WSL. Only install the CUDA toolkit.

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install essential build tools
sudo apt install -y build-essential git curl wget

# Add NVIDIA CUDA repository (for Ubuntu 22.04)
wget https://developer.download.nvidia.com/compute/cuda/repos/wsl-ubuntu/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt update

# Install CUDA toolkit (without drivers - they come from Windows)
sudo apt install -y cuda-toolkit-12-4

# Add CUDA to PATH (add to ~/.bashrc)
echo 'export PATH=/usr/local/cuda/bin:$PATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc

# Verify CUDA installation
nvcc --version
```

## Step 6: Install Python and Create Virtual Environment

```bash
# Install Python 3.11 (recommended)
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip

# Create project directory
mkdir -p ~/projects
cd ~/projects

# Clone the course-builder repository
git clone https://github.com/menkelabs/course-builder.git
cd course-builder

# Create virtual environment
python3.11 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip wheel setuptools
```

## Step 7: Install PyTorch with CUDA Support

```bash
# Ensure venv is activated
source .venv/bin/activate

# Install PyTorch with CUDA 12.4 support
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

# Verify CUDA is available in PyTorch
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"None\"}')"
```

Expected output:
```
CUDA available: True
GPU: NVIDIA GeForce RTX 3080  # (your GPU name)
```

## Step 8: Install SAM (Segment Anything Model)

```bash
# Install SAM from GitHub
pip install git+https://github.com/facebookresearch/segment-anything.git

# Download SAM model weights (~2.4GB for vit_h)
mkdir -p models
cd models

# Option A: vit_h (best quality, requires 16GB+ VRAM)
wget https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth

# Option B: vit_l (good quality, requires 12GB+ VRAM)
# wget https://dl.fbaipublicfiles.com/segment_anything/sam_vit_l_0b3195.pth

# Option C: vit_b (faster, works with 8GB VRAM)
# wget https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth

cd ..
```

## Step 9: Install Grounding DINO

```bash
# Install Grounding DINO
pip install groundingdino-py

# Download Grounding DINO weights (~1.5GB)
cd models
wget https://github.com/IDEA-Research/GroundingDINO/releases/download/v0.1.0-alpha/groundingdino_swint_ogc.pth
cd ..
```

## Step 10: Install Phase2a Dependencies

```bash
# Install phase2a with all dependencies
pip install -e ./phase2a[all]

# Or install individually:
pip install numpy opencv-python Pillow scikit-image shapely geopandas
pip install svgwrite cairosvg click rich pydantic pyyaml
pip install matplotlib PyQt5
pip install pytest
```

## Step 11: Verify Complete Installation

Create a test script `test_gpu_setup.py`:

```python
#!/usr/bin/env python3
"""Verify GPU setup for SAM and Grounding DINO."""

import sys

def check_torch():
    print("=" * 50)
    print("Checking PyTorch...")
    try:
        import torch
        print(f"  PyTorch version: {torch.__version__}")
        print(f"  CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"  CUDA version: {torch.version.cuda}")
            print(f"  GPU: {torch.cuda.get_device_name(0)}")
            print(f"  GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
        return torch.cuda.is_available()
    except ImportError as e:
        print(f"  ERROR: {e}")
        return False

def check_sam():
    print("=" * 50)
    print("Checking SAM...")
    try:
        from segment_anything import sam_model_registry, SamPredictor
        print("  SAM imported successfully")
        return True
    except ImportError as e:
        print(f"  ERROR: {e}")
        return False

def check_groundingdino():
    print("=" * 50)
    print("Checking Grounding DINO...")
    try:
        import groundingdino
        print(f"  Grounding DINO imported successfully")
        return True
    except ImportError as e:
        print(f"  ERROR: {e}")
        return False

def check_phase2a():
    print("=" * 50)
    print("Checking phase2a...")
    try:
        from phase2a.pipeline import masks
        print("  phase2a imported successfully")
        return True
    except ImportError as e:
        print(f"  ERROR: {e}")
        return False

def main():
    results = {
        "PyTorch + CUDA": check_torch(),
        "SAM": check_sam(),
        "Grounding DINO": check_groundingdino(),
        "phase2a": check_phase2a(),
    }
    
    print("=" * 50)
    print("SUMMARY:")
    all_pass = True
    for name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_pass = False
    
    print("=" * 50)
    if all_pass:
        print("All checks passed! Ready to run SAM and Grounding DINO.")
    else:
        print("Some checks failed. Review errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

Run it:
```bash
python test_gpu_setup.py
```

## Step 12: Test SAM with GPU

```bash
# Run a quick SAM test (requires a test image)
python -c "
import torch
from segment_anything import sam_model_registry, SamPredictor
import numpy as np

# Check GPU memory
print(f'GPU Memory before loading: {torch.cuda.memory_allocated()/1e9:.2f} GB')

# Load SAM (use vit_b for testing if you have limited VRAM)
sam = sam_model_registry['vit_h'](checkpoint='models/sam_vit_h_4b8939.pth')
sam = sam.to('cuda')
predictor = SamPredictor(sam)

print(f'GPU Memory after loading: {torch.cuda.memory_allocated()/1e9:.2f} GB')
print('SAM loaded successfully on GPU!')
"
```

## GPU Memory Requirements

| Model | VRAM Required | Notes |
|-------|---------------|-------|
| SAM vit_b | ~4 GB | Fastest, lower quality |
| SAM vit_l | ~8 GB | Good balance |
| SAM vit_h | ~12 GB | Best quality |
| Grounding DINO | ~4 GB | Text-to-box detection |
| Both (vit_h + DINO) | ~16 GB | Full pipeline |

## Troubleshooting

### "CUDA not available" in PyTorch

1. Verify Windows NVIDIA driver:
   ```powershell
   # In Windows PowerShell
   nvidia-smi
   ```

2. Check WSL version:
   ```powershell
   wsl -l -v
   # Should show VERSION 2
   ```

3. Reinstall PyTorch with correct CUDA version:
   ```bash
   pip uninstall torch torchvision torchaudio
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
   ```

### "Out of memory" errors

- Use a smaller SAM model (vit_b or vit_l)
- Process images at lower resolution
- Add `torch.cuda.empty_cache()` between operations

### Grounding DINO build errors

```bash
# Install build dependencies
sudo apt install -y python3.11-dev gcc g++

# Reinstall
pip uninstall groundingdino-py
pip install groundingdino-py
```

### Slow performance

Ensure you're using GPU, not CPU:
```python
import torch
# Force CUDA
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")
```

## Running Phase2a

Once setup is complete, you can run the phase2a pipeline:

```bash
# Activate environment
cd ~/projects/course-builder
source .venv/bin/activate

# Run interactive mask selection
python -m phase2a select-masks \
    --image path/to/satellite_image.png \
    --sam-checkpoint models/sam_vit_h_4b8939.pth \
    --output phase2a_output/

# Run tests
.venv/bin/pytest phase2a/tests/ -v --ignore=phase2a/tests/test_gui_integration.py
```

## File Locations Summary

After setup, your directory structure should look like:

```
~/projects/course-builder/
├── .venv/                          # Python virtual environment
├── models/
│   ├── sam_vit_h_4b8939.pth       # SAM weights (~2.4 GB)
│   └── groundingdino_swint_ogc.pth # DINO weights (~1.5 GB)
├── phase1/                         # QGIS pipeline
├── phase2a/                        # SAM/DINO pipeline
│   ├── pipeline/
│   │   ├── masks.py
│   │   ├── svg.py
│   │   └── ...
│   └── tests/
└── docs/
```

## Quick Reference

```bash
# Start working
cd ~/projects/course-builder
source .venv/bin/activate

# Check GPU status
nvidia-smi

# Check PyTorch CUDA
python -c "import torch; print(torch.cuda.is_available())"

# Run phase2a
python -m phase2a --help
```
