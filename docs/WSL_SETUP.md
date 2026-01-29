# WSL2 Setup for Phase 1 (SegFormer + SAM)

This guide walks through setting up WSL2 on Windows to run **Phase 1** of the course builder: **SegFormer** (semantic segmentation) and **SAM** (Segment Anything Model) for interactive tracing and SVG export. See [ROADMAP.md](ROADMAP.md) for the 4-phase roadmap.

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
mkdir -p checkpoints
cd checkpoints

# Option A: vit_h (best quality, requires 16GB+ VRAM)
wget https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth

# Option B: vit_l (good quality, requires 12GB+ VRAM)
# wget https://dl.fbaipublicfiles.com/segment_anything/sam_vit_l_0b3195.pth

# Option C: vit_b (faster, works with 8GB VRAM)
# wget https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth

cd ..
```

## Step 9: Install Phase 1 Modules (phase1a + phase1_1)

```bash
# phase1a: interactive tracing, SAM, SVG export (Phase 1)
pip install -e "./phase1a[all]"

# phase1_1: SegFormer training (optional; for training on Danish Golf Courses)
pip install -e "./phase1_1[train,inference]"

# Or phase1a only (no SegFormer training):
# pip install -e "./phase1a[sam,dev,gui]"
```

## Step 10: Verify Installation

Create `test_gpu_setup.py` in the project root:

```python
#!/usr/bin/env python3
"""Verify GPU setup for Phase 1 (SAM + phase1a)."""

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

def check_phase1a():
    print("=" * 50)
    print("Checking phase1a...")
    try:
        from phase1a.pipeline import masks
        print("  phase1a imported successfully")
        return True
    except ImportError as e:
        print(f"  ERROR: {e}")
        return False

def check_phase1_1():
    print("=" * 50)
    print("Checking phase1_1 (optional)...")
    try:
        import phase1_1
        print("  phase1_1 imported successfully")
        return True
    except ImportError as e:
        print(f"  Skip (optional): {e}")
        return True  # not required for phase1a

def main():
    results = {
        "PyTorch + CUDA": check_torch(),
        "SAM": check_sam(),
        "phase1a": check_phase1a(),
        "phase1_1": check_phase1_1(),
    }
    print("=" * 50)
    print("SUMMARY:")
    required = ("PyTorch + CUDA", "SAM", "phase1a")
    all_ok = all(results[k] for k in required)
    for name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {name}: {status}")
    print("=" * 50)
    if all_ok:
        print("Phase 1 setup OK. Ready for SAM + phase1a.")
    else:
        print("Some required checks failed. Review errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

Run it:

```bash
python test_gpu_setup.py
```

## Step 11: Quick SAM Test (Optional)

```bash
python -c "
import torch
from segment_anything import sam_model_registry, SamPredictor

print(f'GPU Memory before: {torch.cuda.memory_allocated()/1e9:.2f} GB')
sam = sam_model_registry['vit_h'](checkpoint='checkpoints/sam_vit_h_4b8939.pth')
sam = sam.to('cuda')
predictor = SamPredictor(sam)
print(f'GPU Memory after: {torch.cuda.memory_allocated()/1e9:.2f} GB')
print('SAM loaded on GPU.')
"
```

## GPU Memory (Phase 1)

| Model | VRAM | Notes |
|-------|------|-------|
| SAM vit_b | ~4 GB | Fastest, lower quality |
| SAM vit_l | ~8 GB | Good balance |
| SAM vit_h | ~12 GB | Best quality (recommended) |
| SegFormer-B3 (phase1_1) | ~4–6 GB | Training / inference |

## Troubleshooting

### "CUDA not available" in PyTorch

1. Verify Windows NVIDIA driver: `nvidia-smi` in PowerShell.
2. Check WSL version: `wsl -l -v` → VERSION 2.
3. Reinstall PyTorch with CUDA:
   ```bash
   pip uninstall torch torchvision torchaudio
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
   ```

### "Out of memory" errors

- Use a smaller SAM model (vit_b or vit_l).
- Process images at lower resolution.
- Add `torch.cuda.empty_cache()` between heavy operations.

### Slow performance

Ensure GPU is used:

```python
import torch
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using: {device}")
```

## Running Phase 1

```bash
cd ~/projects/course-builder
source .venv/bin/activate

# Interactive selection (phase1a) – recommended
python -m phase1a select path/to/satellite.png \
  --checkpoint checkpoints/sam_vit_h_4b8939.pth \
  -o phase1a_output

# Full pipeline (phase1a run)
python -m phase1a run path/to/satellite.png \
  --checkpoint checkpoints/sam_vit_h_4b8939.pth \
  -o phase1a_output

# SegFormer training (phase1_1) – optional
python -m phase1_1 train \
  --archive phase1a/resources/archive.zip \
  -o phase1_1_output \
  --epochs 50 --batch-size 8 --device cuda

# Tests
.venv/bin/pytest phase1a/tests/ -v --ignore=phase1a/tests/test_gui_integration.py
```

## Project Layout (Phase 1)

```
~/projects/course-builder/
├── .venv/
├── checkpoints/
│   └── sam_vit_h_4b8939.pth
├── phase1_1/           # SegFormer training & inference
├── phase1a/            # Interactive tracing, SAM, SVG export
│   ├── pipeline/
│   └── tests/
├── archive/            # Old QGIS, DINO, etc. (inactive)
└── docs/
```

## Quick Reference

```bash
cd ~/projects/course-builder && source .venv/bin/activate
nvidia-smi
python -c "import torch; print(torch.cuda.is_available())"
python -m phase1a --help
python -m phase1_1 --help
```
