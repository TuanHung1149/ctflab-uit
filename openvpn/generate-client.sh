#!/bin/bash
# Generate OpenVPN client certificate and return .ovpn config
# Usage: generate-client.sh <slot_number> <server_ip>
set -euo pipefail

SLOT="${1:?Usage: generate-client.sh <slot> <server_ip>}"
SERVER_IP="${2:-$(hostname -I | awk '{print $1}')}"
CLIENT_NAME="ctflab_slot_${SLOT}"
EASYRSA_DIR="/etc/openvpn/easy-rsa"
SUBNET_PREFIX="10.100"

# Check PKI exists
if [ ! -d "$EASYRSA_DIR/pki" ]; then
    echo "ERROR: PKI not initialized. Run setup-server.sh first." >&2
    exit 1
fi

# Generate client cert if not exists
if [ ! -f "$EASYRSA_DIR/pki/issued/${CLIENT_NAME}.crt" ]; then
    cd "$EASYRSA_DIR"
    EASYRSA_BATCH=1 ./easyrsa build-client-full "$CLIENT_NAME" nopass 2>/dev/null
fi

# Read certs
CA_CERT=$(cat "$EASYRSA_DIR/pki/ca.crt")
CLIENT_CERT=$(sed -n '/BEGIN CERTIFICATE/,/END CERTIFICATE/p' "$EASYRSA_DIR/pki/issued/${CLIENT_NAME}.crt")
CLIENT_KEY=$(cat "$EASYRSA_DIR/pki/private/${CLIENT_NAME}.key")
TA_KEY=""
if [ -f "/etc/openvpn/ta.key" ]; then
    TA_KEY=$(cat /etc/openvpn/ta.key)
fi

# Generate .ovpn config
cat <<EOF
client
dev tun
proto udp
remote ${SERVER_IP} 1194
resolv-retry infinite
nobind
persist-key
persist-tun
remote-cert-tls server
verb 3

# Split tunnel - only route CTF subnet through VPN
route-nopull
route ${SUBNET_PREFIX}.${SLOT}.0 255.255.255.0

# DNS: use box's DNS for domain resolution
dhcp-option DNS ${SUBNET_PREFIX}.${SLOT}.2

<ca>
${CA_CERT}
</ca>
<cert>
${CLIENT_CERT}
</cert>
<key>
${CLIENT_KEY}
</key>
EOF

if [ -n "$TA_KEY" ]; then
cat <<EOF
key-direction 1
<tls-auth>
${TA_KEY}
</tls-auth>
EOF
fi
