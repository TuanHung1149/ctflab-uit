#!/bin/bash
# CTFLab UIT - Full deployment script
# Run this on a fresh Ubuntu 22.04+ server
set -euo pipefail

echo "============================================"
echo "  CTFLab UIT - Deployment Script"
echo "============================================"

# Check root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo)"
    exit 1
fi

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "[1/6] Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
else
    echo "[1/6] Docker already installed"
fi

# Install Docker Compose plugin if not present
if ! docker compose version &> /dev/null; then
    echo "[2/6] Installing Docker Compose..."
    apt-get update
    apt-get install -y docker-compose-plugin
else
    echo "[2/6] Docker Compose already installed"
fi

# Install WireGuard
if ! command -v wg &> /dev/null; then
    echo "[3/6] Installing WireGuard..."
    apt-get update
    apt-get install -y wireguard-tools
else
    echo "[3/6] WireGuard already installed"
fi

# Setup WireGuard server
echo "[4/6] Setting up WireGuard server..."
bash wireguard/setup-server.sh

# Ensure runtime directories exist
mkdir -p vpn-configs

# Build the infinity box Docker image
echo "[5/6] Building infinity box Docker image..."
docker build -t ctflab/infinity ./boxes/infinity/

# Start CTFd platform
echo "[6/6] Starting CTFd platform..."
docker compose up -d --build

echo ""
echo "============================================"
echo "  Deployment Complete!"
echo "============================================"
echo ""
echo "  CTFd Web UI:    http://$(hostname -I | awk '{print $1}'):8080"
echo "  WireGuard Port: 51820/udp"
echo ""
echo "  Next steps:"
echo "  1. Open CTFd in browser and create admin account"
echo "  2. Create a challenge of type 'ctflab'"
echo "  3. Set docker_image to 'ctflab/infinity'"
echo "  4. Students can now launch instances and hack!"
echo ""
