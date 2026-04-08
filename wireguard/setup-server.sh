#!/bin/bash
set -euo pipefail

echo "=== CTFLab WireGuard Server Setup ==="

# Install WireGuard
if ! command -v wg &> /dev/null; then
    echo "[1/4] Installing WireGuard..."
    apt-get update
    apt-get install -y wireguard-tools
else
    echo "[1/4] WireGuard already installed"
fi

# Enable IP forwarding
echo "[2/4] Enabling IP forwarding..."
sysctl -w net.ipv4.ip_forward=1
grep -q '^net.ipv4.ip_forward=1' /etc/sysctl.conf \
    || echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf

# Generate server keypair if not exists
WG_DIR="/etc/wireguard"
mkdir -p "${WG_DIR}/clients"

if [ ! -f "${WG_DIR}/server_private.key" ]; then
    echo "[3/4] Generating server keypair..."
    wg genkey | tee "${WG_DIR}/server_private.key" | wg pubkey > "${WG_DIR}/server_public.key"
    chmod 600 "${WG_DIR}/server_private.key"
else
    echo "[3/4] Server keypair already exists"
fi

SERVER_PRIVKEY=$(cat "${WG_DIR}/server_private.key")

# Create slot registry
if [ ! -f "${WG_DIR}/slots.json" ]; then
    echo "{}" > "${WG_DIR}/slots.json"
fi

# Create wg0 config
echo "[4/4] Creating WireGuard config..."
cat > "${WG_DIR}/wg0.conf" <<EOF
[Interface]
Address = 10.200.0.1/24
ListenPort = 51820
PrivateKey = ${SERVER_PRIVKEY}
SaveConfig = false

# Forwarding and NAT handled by fix-vpn-routing.sh / CTFLAB_ISOLATION
PostUp = sysctl -w net.ipv4.ip_forward=1
EOF

chmod 600 "${WG_DIR}/wg0.conf"

# Re-add existing peers from client dirs
for client_dir in "${WG_DIR}/clients"/*/; do
    [ -d "$client_dir" ] || continue
    username=$(basename "$client_dir")
    pubkey_file="${client_dir}/public.key"
    slot_file="${client_dir}/slot"
    if [ -f "$pubkey_file" ] && [ -f "$slot_file" ]; then
        pubkey=$(cat "$pubkey_file")
        slot=$(cat "$slot_file")
        vpn_ip="10.200.0.$((slot + 1))"
        echo "" >> "${WG_DIR}/wg0.conf"
        echo "# ${username} (slot ${slot})" >> "${WG_DIR}/wg0.conf"
        echo "[Peer]" >> "${WG_DIR}/wg0.conf"
        echo "PublicKey = ${pubkey}" >> "${WG_DIR}/wg0.conf"
        echo "AllowedIPs = ${vpn_ip}/32" >> "${WG_DIR}/wg0.conf"
    fi
done

# Start/restart WireGuard
systemctl enable wg-quick@wg0 2>/dev/null || true

if systemctl is-active --quiet wg-quick@wg0; then
    # Restart to pick up config changes
    systemctl restart wg-quick@wg0
else
    systemctl start wg-quick@wg0
fi

echo ""
echo "=== WireGuard Server Setup Complete ==="
echo "Server: 10.200.0.1, Port: 51820/udp"
echo "Public Key: $(cat "${WG_DIR}/server_public.key")"
echo ""
