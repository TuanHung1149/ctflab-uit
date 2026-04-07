#!/bin/bash
set -euo pipefail

USERNAME="${1:?Usage: update-vpn-route.sh <username> <slot|remove>}"
ACTION="${2:?Usage: update-vpn-route.sh <username> <slot|remove>}"
CCD_DIR="/etc/openvpn/ccd"

if [[ ! "$USERNAME" =~ ^[A-Za-z0-9_.-]+$ ]]; then
    echo "Invalid username: ${USERNAME}" >&2
    exit 1
fi

mkdir -p "${CCD_DIR}"
CCD_FILE="${CCD_DIR}/${USERNAME}"

if [ "${ACTION}" = "remove" ]; then
    : > "${CCD_FILE}"
    echo "Cleared CCD route for ${USERNAME}"
    exit 0
fi

if [[ ! "${ACTION}" =~ ^[0-9]+$ ]]; then
    echo "Invalid slot: ${ACTION}" >&2
    exit 1
fi

SLOT="${ACTION}"
if [ "${SLOT}" -lt 1 ] || [ "${SLOT}" -gt 50 ]; then
    echo "Slot out of range: ${SLOT}" >&2
    exit 1
fi

VPN_IP="10.200.0.$((SLOT + 1))"
BOX_SUBNET="10.100.${SLOT}.0"
BOX_MASK="255.255.255.0"

cat > "${CCD_FILE}" <<EOF
ifconfig-push ${VPN_IP} 255.255.0.0
push "route ${BOX_SUBNET} ${BOX_MASK}"
push "dhcp-option DNS 10.100.${SLOT}.2"
EOF

echo "Updated CCD route for ${USERNAME} -> slot ${SLOT}"
