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

# Install OpenVPN and EasyRSA
if ! command -v openvpn &> /dev/null; then
    echo "[3/6] Installing OpenVPN + EasyRSA..."
    apt-get install -y openvpn easy-rsa
else
    echo "[3/6] OpenVPN already installed"
fi

# Setup OpenVPN server
echo "[4/6] Setting up OpenVPN server..."
if [ ! -d "/etc/openvpn/easy-rsa/pki" ]; then
    bash openvpn/setup-server.sh
else
    echo "  OpenVPN PKI already exists, skipping setup"
fi

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
echo "  CTFd Web UI:    http://$(hostname -I | awk '{print $1}'):8000"
echo "  OpenVPN Port:   1194/udp"
echo ""
echo "  Next steps:"
echo "  1. Open CTFd in browser and create admin account"
echo "  2. Create a challenge of type 'ctflab'"
echo "  3. Set docker_image to 'ctflab/infinity'"
echo "  4. Students can now launch instances and hack!"
echo ""
