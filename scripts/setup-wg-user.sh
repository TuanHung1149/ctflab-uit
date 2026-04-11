#!/bin/bash
set -euo pipefail

# Generate or retrieve a WireGuard config for a user.
# Usage: setup-wg-user.sh <username> <server_ip> [wg_port]
#
# - Assigns a FIXED slot (persisted in /etc/wireguard/slots.json)
# - Generates keypair once per user
# - Outputs .conf to /vpn-configs/<username>.conf
# - Writes pending wg operation for host-side sync

USERNAME="${1:?Usage: setup-wg-user.sh <username> <server_ip> [wg_port]}"
SERVER_IP="${2:-45.122.249.68}"
WG_PORT="${3:-11194}"
WG_DIR="/etc/wireguard"
CLIENT_DIR="${WG_DIR}/clients/${USERNAME}"
SLOTS_FILE="${WG_DIR}/slots.json"
OUT_DIR="/vpn-configs"
PENDING="${WG_DIR}/pending-ops"

# Validate username
if [[ ! "$USERNAME" =~ ^[A-Za-z0-9_.-]+$ ]]; then
    echo "Invalid username: ${USERNAME}" >&2
    exit 1
fi

# Check server is set up
if [ ! -f "${WG_DIR}/server_public.key" ]; then
    echo "WireGuard server not initialized. Run wireguard/setup-server.sh first." >&2
    exit 1
fi

SERVER_PUBKEY=$(cat "${WG_DIR}/server_public.key")

mkdir -p "${CLIENT_DIR}" "${OUT_DIR}"

# --- Assign fixed slot ---
if [ ! -f "${SLOTS_FILE}" ]; then
    echo "{}" > "${SLOTS_FILE}"
fi

# Use flock for atomic slot assignment
(
    flock -w 10 200 || { echo "Failed to lock slots file" >&2; exit 1; }

    SLOT=$(python3 -c "
import json, sys
with open('${SLOTS_FILE}') as f:
    slots = json.load(f)
if '${USERNAME}' in slots:
    print(slots['${USERNAME}'])
    sys.exit(0)
used = set(slots.values())
for s in range(1, 51):
    if s not in used:
        slots['${USERNAME}'] = s
        with open('${SLOTS_FILE}', 'w') as f:
            json.dump(slots, f, indent=2)
        print(s)
        sys.exit(0)
print('ERROR: no free slots', file=sys.stderr)
sys.exit(1)
")

    echo "${SLOT}" > "${CLIENT_DIR}/slot"

) 200>"${SLOTS_FILE}.lock"

SLOT=$(cat "${CLIENT_DIR}/slot")
VPN_IP="10.200.0.$((SLOT + 1))"

# --- Generate keypair if not exists ---
if [ ! -f "${CLIENT_DIR}/private.key" ]; then
    wg genkey | tee "${CLIENT_DIR}/private.key" | wg pubkey > "${CLIENT_DIR}/public.key"
    chmod 600 "${CLIENT_DIR}/private.key"
fi

CLIENT_PRIVKEY=$(cat "${CLIENT_DIR}/private.key")
CLIENT_PUBKEY=$(cat "${CLIENT_DIR}/public.key")

# --- Add peer to wg0.conf (persistent) ---
if ! grep -q "${CLIENT_PUBKEY}" "${WG_DIR}/wg0.conf" 2>/dev/null; then
    cat >> "${WG_DIR}/wg0.conf" <<EOF

# ${USERNAME} (slot ${SLOT})
[Peer]
PublicKey = ${CLIENT_PUBKEY}
AllowedIPs = ${VPN_IP}/32
EOF
fi

# --- Queue wg set for host-side sync ---
echo "wg set wg0 peer ${CLIENT_PUBKEY} allowed-ips ${VPN_IP}/32" >> "${PENDING}" 2>/dev/null || true

# --- Try direct wg set (works on host, fails silently in container) ---
wg set wg0 peer "${CLIENT_PUBKEY}" allowed-ips "${VPN_IP}/32" 2>/dev/null || true

# --- Generate client config ---
cat > "${OUT_DIR}/${USERNAME}.conf" <<EOF
[Interface]
PrivateKey = ${CLIENT_PRIVKEY}
Address = ${VPN_IP}/32

[Peer]
PublicKey = ${SERVER_PUBKEY}
Endpoint = ${SERVER_IP}:${WG_PORT}
AllowedIPs = 10.100.0.0/16, 10.200.0.1/32
PersistentKeepalive = 25
EOF

chmod 600 "${OUT_DIR}/${USERNAME}.conf"
echo "Generated ${OUT_DIR}/${USERNAME}.conf (slot=${SLOT}, ip=${VPN_IP})"
