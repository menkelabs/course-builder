#!/bin/bash
# QGIS Installation Script for Ubuntu/Debian
# Run with: sudo bash install_qgis.sh

set -e  # Exit on error

echo "=========================================="
echo "QGIS Installation Script"
echo "=========================================="
echo ""

# Step 1: Update system packages
echo "[1/6] Updating system packages..."
apt update
apt install -y ca-certificates gnupg lsb-release software-properties-common

# Step 2: Create keyrings directory
echo "[2/6] Creating keyrings directory..."
mkdir -p /etc/apt/keyrings

# Step 3: Download QGIS archive keyring
echo "[3/6] Downloading QGIS archive keyring..."
wget -O /etc/apt/keyrings/qgis-archive-keyring.gpg https://download.qgis.org/downloads/qgis-archive-keyring.gpg

# Step 4: Add QGIS repository
echo "[4/6] Adding QGIS repository..."
ARCH=$(dpkg --print-architecture)
CODENAME=$(lsb_release -cs)
echo "deb [arch=${ARCH} signed-by=/etc/apt/keyrings/qgis-archive-keyring.gpg] https://qgis.org/ubuntu-ltr ${CODENAME} main" | tee /etc/apt/sources.list.d/qgis.list > /dev/null

# Step 5: Update package lists
echo "[5/6] Updating package lists..."
apt update

# Step 6: Install QGIS
echo "[6/6] Installing QGIS..."
apt install -y qgis qgis-plugin-grass

echo ""
echo "=========================================="
echo "QGIS Installation Complete!"
echo "=========================================="
echo ""
echo "Verifying installation..."

# Verify installation
if command -v qgis_process &> /dev/null; then
    echo "✓ qgis_process found: $(which qgis_process)"
    qgis_process --version
else
    echo "⚠ qgis_process not in PATH, checking common locations..."
    if [ -f "/usr/bin/qgis_process" ]; then
        echo "✓ Found at /usr/bin/qgis_process"
    elif [ -f "/usr/lib/qgis/bin/qgis_process" ]; then
        echo "✓ Found at /usr/lib/qgis/bin/qgis_process"
        echo "  Consider adding to PATH or creating symlink:"
        echo "  sudo ln -s /usr/lib/qgis/bin/qgis_process /usr/local/bin/qgis_process"
    else
        echo "✗ qgis_process not found. Installation may have failed."
        exit 1
    fi
fi

echo ""
echo "Next steps:"
echo "1. Test QGIS: qgis_process --version"
echo "2. List algorithms: qgis_process list"
echo "3. Configure Phase 1: see QGIS_SETUP.md"
