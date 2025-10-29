#!/bin/bash

# Exit on any error
set -e

# Always run from this script's directory to ensure correct context
cd "$(cd "$(dirname "$0")" && pwd)"

# Parse args
REBUILD_IMAGES=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --rebuild-images|--force-rebuild)
            REBUILD_IMAGES=true
            shift
            ;;
        *)
            echo "Unknown argument: $1" && exit 1
            ;;
    esac
done

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    echo "Loading environment variables from .env file..."
    set -a
    source .env
    set +a
fi

echo "=========================================="
echo "MLE-bench Setup Script"
echo "=========================================="

# Check if Docker is installed; if not, install it (Debian/Ubuntu)
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Installing Docker (requires sudo)..."
    export DEBIAN_FRONTEND=noninteractive
    # Base prerequisites
    sudo apt-get update -y
    sudo apt-get install -y ca-certificates curl gnupg lsb-release apt-transport-https

    # Ensure keyrings directory exists
    if [ ! -d /etc/apt/keyrings ]; then
        sudo install -m 0755 -d /etc/apt/keyrings
    fi

    if . /etc/os-release; then
        if [ "$ID" = "debian" ]; then
            if [ ! -f /etc/apt/keyrings/docker.gpg ]; then
                curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor --batch --yes -o /etc/apt/keyrings/docker.gpg
            fi
            echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian ${VERSION_CODENAME} stable" \
              | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
        elif [ "$ID" = "ubuntu" ]; then
            if [ ! -f /etc/apt/keyrings/docker.gpg ]; then
                curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor --batch --yes -o /etc/apt/keyrings/docker.gpg
            fi
            echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
              | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
        else
            echo "Unsupported OS ($ID) for automatic Docker install. Please install Docker manually: https://docs.docker.com/engine/install/"
            exit 1
        fi
    fi

    sudo apt-get update -y
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    sudo systemctl enable --now docker || true

    # Allow current user to use Docker without sudo in future sessions
    if ! getent group docker >/dev/null; then
        sudo groupadd docker || true
    fi
    if ! groups "$USER" | grep -q "\bdocker\b"; then
        sudo usermod -aG docker "$USER" || true
        echo "Added $USER to 'docker' group. You may need to log out/in for this to take effect."
    fi

    # Re-check docker availability
    if command -v docker &> /dev/null; then
        echo "✓ Docker installed."
    else
        echo "Warning: Docker installation may not have completed successfully."
    fi
else
    echo "✓ Docker is installed."
fi

# Determine docker command (fallback to sudo if current session lacks group membership)
DOCKER="docker"
if ! $DOCKER info >/dev/null 2>&1; then
    DOCKER="sudo docker"
fi

# Check if running with sudo/root for system package installation
if [ "$EUID" -ne 0 ]; then 
    echo "Note: This script requires sudo privileges for installing system packages."
    echo "You may be prompted for your password."
fi

# Optional: CUDA/NVIDIA driver + Container Toolkit setup (idempotent)
echo ""
echo "Checking NVIDIA GPU / CUDA setup..."
if command -v nvidia-smi &> /dev/null; then
    echo "✓ nvidia-smi found. Skipping CUDA driver install."
else
    echo "NVIDIA driver not detected. Installing CUDA driver and NVIDIA Container Toolkit..."
    export DEBIAN_FRONTEND=noninteractive
    # Install kernel headers for running kernel (for DKMS builds)
    KVER=$(uname -r)
    sudo apt-get update -y
    sudo apt-get install -y linux-headers-$KVER build-essential dkms curl ca-certificates gnupg

    # Add NVIDIA Container Toolkit repo
    if [ ! -f /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg ]; then
        curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor --batch --yes -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
        curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
          | sed "s#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g" \
          | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list >/dev/null
    fi

    # Add CUDA repo (Debian 12/Ubuntu equivalents)
    if [ ! -f /usr/share/keyrings/cuda-archive-keyring.gpg ]; then
        if . /etc/os-release; then
            if [ "$ID" = "debian" ] && [ "$VERSION_ID" = "12" ]; then
                wget -qO- https://developer.download.nvidia.com/compute/cuda/repos/debian12/x86_64/3bf863cc.pub | \
                  sudo gpg --dearmor --batch --yes -o /usr/share/keyrings/cuda-archive-keyring.gpg
                echo "deb [signed-by=/usr/share/keyrings/cuda-archive-keyring.gpg arch=amd64] https://developer.download.nvidia.com/compute/cuda/repos/debian12/x86_64/ /" \
                  | sudo tee /etc/apt/sources.list.d/cuda-debian12-x86_64.list >/dev/null
            fi
        fi
    fi

    sudo apt-get update -y
    # Install container toolkit and configure Docker runtime
    sudo apt-get install -y nvidia-container-toolkit
    sudo nvidia-ctk runtime configure --runtime=docker || true
    sudo systemctl restart docker || true

    # Install CUDA drivers meta-package
    sudo apt-get install -y cuda-drivers || true

    # Try to load the module and verify
    sudo modprobe nvidia || true
    if command -v nvidia-smi &> /dev/null && nvidia-smi &> /dev/null; then
        echo "✓ NVIDIA driver installed and active."
    else
        echo "Note: NVIDIA driver installed but not yet active. A reboot may be required."
    fi
fi

# Install Sysbox
echo ""
echo "Installing Sysbox..."
echo "Sysbox provides enhanced container security for running agents."

# Check if sysbox is already installed
if systemctl is-active --quiet sysbox 2>/dev/null; then
    echo "Sysbox is already installed and running."
else
    # Update package lists
    sudo apt update

    # Install prerequisites
    sudo apt install -y wget curl apt-transport-https fuse rsync

    # Remove any existing Docker containers to allow Sysbox post-install to proceed
    CONTAINERS=$($DOCKER ps -aq || true)
    if [ -n "$CONTAINERS" ]; then
        echo "Removing existing Docker containers before Sysbox install..."
        $DOCKER rm -f $CONTAINERS || true
    fi

    # Download the latest Sysbox package from GitHub releases
    echo "Fetching latest Sysbox release URL..."
    SYSBOX_DEB_URL=$(curl -s https://api.github.com/repos/nestybox/sysbox/releases/latest | grep browser_download_url | grep 'sysbox-ce_.*linux_amd64.deb' | head -n1 | cut -d '"' -f 4)
    if [ -z "$SYSBOX_DEB_URL" ]; then
        echo "Error: Could not resolve Sysbox release URL from GitHub."
        exit 1
    fi

    echo "Downloading Sysbox from $SYSBOX_DEB_URL ..."
    wget -q "$SYSBOX_DEB_URL" -O sysbox-ce.deb

    # Install Sysbox
    echo "Installing Sysbox (this may take a moment)..."
    sudo apt install -y ./sysbox-ce.deb || true

    # Clean up downloaded package
    rm -f sysbox-ce.deb

    # Ensure Docker is restarted so it picks up the sysbox runtime
    sudo systemctl restart docker || true
    sleep 2

    # Verify Sysbox services are running
    if systemctl is-active --quiet sysbox; then
        echo "✓ Sysbox installed and running successfully!"
    else
        echo "Warning: Sysbox may not be running correctly."
        echo "Check status with: sudo systemctl status sysbox"
    fi
fi

echo ""
echo "Setting up Python virtual environment for MLE-bench..."

# Check if venv module is available
if ! python3 -c "import venv" &> /dev/null; then
    echo "Error: Python venv module is not available."
    echo "On Debian/Ubuntu systems, install it with:"
    echo "  sudo apt update && sudo apt install python3.11-venv"
    echo ""
    echo "After installing python3.11-venv, run this script again."
    exit 1
fi

# Create virtual environment in ./.venv
python3 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate

echo "Virtual environment created and activated."

# Install Git-LFS if not already installed and pull LFS files
# (Some MLE-bench competition data is stored using Git-LFS)
if command -v git-lfs &> /dev/null; then
    echo "Git-LFS found. Fetching and pulling LFS files..."
    git lfs fetch --all
    git lfs pull
else
    echo "Warning: Git-LFS not found. Some competition data may not be available."
    echo "Install Git-LFS from https://git-lfs.com/ if you need the full dataset."
fi

# Install MLE-bench in editable mode
echo "Installing MLE-bench..."
pip install -e .

# Build Docker images required to run agents
echo ""
echo "Checking Docker images..."

if [ "$REBUILD_IMAGES" = true ]; then
    echo "Forcing rebuild of Docker images (no cache)..."
fi

# Base environment image
if [ "$REBUILD_IMAGES" = true ]; then
    echo "Rebuilding 'mlebench-env' image (this may take several minutes)..."
    docker build --no-cache --platform=linux/amd64 -t mlebench-env -f environment/Dockerfile .
else
    if docker image inspect mlebench-env &> /dev/null; then
        echo "✓ Docker image 'mlebench-env' already exists, skipping build."
    else
        echo "Building 'mlebench-env' image (this may take several minutes)..."
        docker build --platform=linux/amd64 -t mlebench-env -f environment/Dockerfile .
    fi
fi

# Dummy agent image
export SUBMISSION_DIR=/home/submission
export LOGS_DIR=/home/logs
export CODE_DIR=/home/code
export AGENT_DIR=/home/agent

if [ "$REBUILD_IMAGES" = true ]; then
    echo "Rebuilding 'dummy' agent image (this may take several minutes)..."
    docker build --no-cache --platform=linux/amd64 -t dummy agents/dummy/ \
      --build-arg SUBMISSION_DIR=$SUBMISSION_DIR \
      --build-arg LOGS_DIR=$LOGS_DIR \
      --build-arg CODE_DIR=$CODE_DIR \
      --build-arg AGENT_DIR=$AGENT_DIR
else
    if docker image inspect dummy &> /dev/null; then
        echo "✓ Docker image 'dummy' already exists, skipping build."
    else
        echo "Building 'dummy' agent image (this may take several minutes)..."
        docker build --platform=linux/amd64 -t dummy agents/dummy/ \
          --build-arg SUBMISSION_DIR=$SUBMISSION_DIR \
          --build-arg LOGS_DIR=$LOGS_DIR \
          --build-arg CODE_DIR=$CODE_DIR \
          --build-arg AGENT_DIR=$AGENT_DIR
    fi
fi

# Aide agent image (used by default runs)
if [ "$REBUILD_IMAGES" = true ]; then
    echo "Rebuilding 'aide' agent image (this may take several minutes)..."
    docker build --no-cache --platform=linux/amd64 -t aide agents/aide/ \
      --build-arg SUBMISSION_DIR=$SUBMISSION_DIR \
      --build-arg LOGS_DIR=$LOGS_DIR \
      --build-arg CODE_DIR=$CODE_DIR \
      --build-arg AGENT_DIR=$AGENT_DIR
else
    if docker image inspect aide &> /dev/null; then
        echo "✓ Docker image 'aide' already exists, skipping build."
    else
        echo "Building 'aide' agent image (this may take several minutes)..."
        docker build --platform=linux/amd64 -t aide agents/aide/ \
          --build-arg SUBMISSION_DIR=$SUBMISSION_DIR \
          --build-arg LOGS_DIR=$LOGS_DIR \
          --build-arg CODE_DIR=$CODE_DIR \
          --build-arg AGENT_DIR=$AGENT_DIR
    fi
fi

echo ""
echo "Local competition preparation"
echo "------------------------------------------"
echo "We no longer auto-run a local prepare here."
echo "Open scripts/add_new_competition/LLM_ADD_COMPETITION_GUIDE.md in Cursor"
echo "and follow the step-by-step instructions to add and prepare competitions."
echo "(Helper available: scripts/add_new_competition/prepare_local_competition.py)"

echo "Setup complete! To activate the virtual environment in future sessions, run:"
echo "source .venv/bin/activate"
