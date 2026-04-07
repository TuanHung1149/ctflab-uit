#!/bin/bash
set -euo pipefail

echo "=== CTFLab OpenVPN Server Setup ==="

# Install OpenVPN and EasyRSA
apt-get update
apt-get install -y openvpn easy-rsa

# Setup EasyRSA
EASYRSA_DIR="/etc/openvpn/easy-rsa"
mkdir -p "$EASYRSA_DIR"

if [ ! -f "$EASYRSA_DIR/easyrsa" ]; then
    cp -r /usr/share/easy-rsa/* "$EASYRSA_DIR/"
fi

cd "$EASYRSA_DIR"
export EASYRSA_BATCH=1
export EASYRSA_REQ_CN="CTFLab-CA"

if [ ! -d "$EASYRSA_DIR/pki" ]; then
    ./easyrsa init-pki
    ./easyrsa build-ca nopass
    ./easyrsa gen-dh
fi

if [ ! -f "$EASYRSA_DIR/pki/issued/server.crt" ]; then
    ./easyrsa build-server-full server nopass
fi

# Generate TLS auth key
if [ ! -f /etc/openvpn/ta.key ]; then
    openvpn --genkey secret /etc/openvpn/ta.key
fi

# Enable IP forwarding
sysctl -w net.ipv4.ip_forward=1
grep -q '^net.ipv4.ip_forward=1' /etc/sysctl.conf \
    || echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf

# Create server config
cat > /etc/openvpn/server.conf <<'EOF'
port 1194
proto udp
dev tun
topology subnet
ca /etc/openvpn/easy-rsa/pki/ca.crt
cert /etc/openvpn/easy-rsa/pki/issued/server.crt
key /etc/openvpn/easy-rsa/pki/private/server.key
dh /etc/openvpn/easy-rsa/pki/dh.pem
tls-auth /etc/openvpn/ta.key 0
server 10.200.0.0 255.255.0.0
keepalive 10 120
cipher AES-256-GCM
persist-key
persist-tun
status /var/log/openvpn-status.log
log /var/log/openvpn.log
verb 3
# CRL for revoked certs
# crl-verify /etc/openvpn/easy-rsa/pki/crl.pem
# Client config directory for per-user routing
client-config-dir /etc/openvpn/ccd
EOF

# Create client config directory
mkdir -p /etc/openvpn/ccd

# Start OpenVPN
systemctl enable openvpn@server
if systemctl is-active --quiet openvpn@server; then
    systemctl restart openvpn@server
else
    systemctl start openvpn@server
fi

echo "=== OpenVPN Server Setup Complete ==="
echo "Server is running on port 1194/udp"
