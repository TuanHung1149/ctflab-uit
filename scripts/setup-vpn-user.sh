#!/bin/bash
set -euo pipefail

USERNAME="${1:?Usage: setup-vpn-user.sh <username> <server_ip>}"
SERVER_IP="${2:-152.42.233.178}"
EASYRSA_DIR="/etc/openvpn/easy-rsa"
PKI_DIR="${EASYRSA_DIR}/pki"
CCD_DIR="/etc/openvpn/ccd"
OUT_DIR="/vpn-configs"

if [[ ! "$USERNAME" =~ ^[A-Za-z0-9_.-]+$ ]]; then
    echo "Invalid username: ${USERNAME}" >&2
    exit 1
fi

if [ ! -f "${EASYRSA_DIR}/easyrsa" ] || [ ! -d "${PKI_DIR}" ]; then
    echo "OpenVPN PKI is not initialized" >&2
    exit 1
fi

mkdir -p "${CCD_DIR}" "${OUT_DIR}"

if [ ! -f "${PKI_DIR}/issued/${USERNAME}.crt" ]; then
    (
        cd "${EASYRSA_DIR}"
        EASYRSA_BATCH=1 ./easyrsa build-client-full "${USERNAME}" nopass
    )
fi

touch "${CCD_DIR}/${USERNAME}"

CA_CERT="$(cat "${PKI_DIR}/ca.crt")"
CLIENT_CERT="$(sed -n '/BEGIN CERTIFICATE/,/END CERTIFICATE/p' "${PKI_DIR}/issued/${USERNAME}.crt")"
CLIENT_KEY="$(cat "${PKI_DIR}/private/${USERNAME}.key")"

{
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
pull
pull-filter ignore redirect-gateway
auth-nocache
verb 3

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

    if [ -f /etc/openvpn/ta.key ]; then
        cat <<EOF
key-direction 1
<tls-auth>
$(cat /etc/openvpn/ta.key)
</tls-auth>
EOF
    fi
} > "${OUT_DIR}/${USERNAME}.ovpn"

echo "Generated ${OUT_DIR}/${USERNAME}.ovpn"
