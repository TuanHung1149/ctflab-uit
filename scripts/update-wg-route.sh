#!/bin/bash
set -euo pipefail

# Update WireGuard peer's AllowedIPs when a box starts/stops.
# Usage: update-wg-route.sh <username> <slot|remove>
#
# Updates both wg0.conf (persistent) and queues wg set (applied by cron).

USERNAME="${1:?Usage: update-wg-route.sh <username> <slot|remove>}"
ACTION="${2:?Usage: update-wg-route.sh <username> <slot|remove>}"
WG_DIR="/etc/wireguard"
CLIENT_DIR="${WG_DIR}/clients/${USERNAME}"
PENDING="${WG_DIR}/pending-ops"
WG_CONF="${WG_DIR}/wg0.conf"

# Validate
if [[ ! "$USERNAME" =~ ^[A-Za-z0-9_.-]+$ ]]; then
    echo "Invalid username: ${USERNAME}" >&2
    exit 1
fi

if [ ! -f "${CLIENT_DIR}/public.key" ]; then
    echo "No WireGuard keys for ${USERNAME}" >&2
    exit 1
fi

CLIENT_PUBKEY=$(cat "${CLIENT_DIR}/public.key")

if [ ! -f "${CLIENT_DIR}/slot" ]; then
    echo "No slot assigned for ${USERNAME}" >&2
    exit 1
fi

USER_SLOT=$(cat "${CLIENT_DIR}/slot")
VPN_IP="10.200.0.$((USER_SLOT + 1))"

if [ "${ACTION}" = "remove" ]; then
    NEW_ALLOWED="${VPN_IP}/32"

    # Update wg0.conf: replace AllowedIPs for this peer
    if [ -f "$WG_CONF" ]; then
        python3 -c "
import re, sys
with open('${WG_CONF}') as f:
    content = f.read()
# Find and replace AllowedIPs for this peer's PublicKey
lines = content.split('\n')
new_lines = []
found_peer = False
for i, line in enumerate(lines):
    if line.strip().startswith('PublicKey') and '${CLIENT_PUBKEY}' in line:
        found_peer = True
    elif found_peer and line.strip().startswith('AllowedIPs'):
        new_lines.append('AllowedIPs = ${NEW_ALLOWED}')
        found_peer = False
        continue
    elif found_peer and (line.strip().startswith('[') or line.strip() == ''):
        found_peer = False
    new_lines.append(line)
with open('${WG_CONF}', 'w') as f:
    f.write('\n'.join(new_lines))
"
    fi

    # Queue + try direct
    echo "wg set wg0 peer ${CLIENT_PUBKEY} allowed-ips ${NEW_ALLOWED}" >> "${PENDING}" 2>/dev/null || true
    wg set wg0 peer "${CLIENT_PUBKEY}" allowed-ips "${NEW_ALLOWED}" 2>/dev/null || true
    echo "Removed Docker route for ${USERNAME} (kept VPN IP ${VPN_IP})"
    exit 0
fi

# Validate slot number
if [[ ! "${ACTION}" =~ ^[0-9]+$ ]]; then
    echo "Invalid slot: ${ACTION}" >&2
    exit 1
fi

SLOT="${ACTION}"
if [ "${SLOT}" -lt 1 ] || [ "${SLOT}" -gt 50 ]; then
    echo "Slot out of range: ${SLOT}" >&2
    exit 1
fi

BOX_SUBNET="10.100.${SLOT}.0/24"
NEW_ALLOWED="${VPN_IP}/32,${BOX_SUBNET}"

# Update wg0.conf: replace AllowedIPs for this peer
if [ -f "$WG_CONF" ]; then
    python3 -c "
import re, sys
with open('${WG_CONF}') as f:
    content = f.read()
lines = content.split('\n')
new_lines = []
found_peer = False
for i, line in enumerate(lines):
    if line.strip().startswith('PublicKey') and '${CLIENT_PUBKEY}' in line:
        found_peer = True
    elif found_peer and line.strip().startswith('AllowedIPs'):
        new_lines.append('AllowedIPs = ${NEW_ALLOWED}')
        found_peer = False
        continue
    elif found_peer and (line.strip().startswith('[') or line.strip() == ''):
        found_peer = False
    new_lines.append(line)
with open('${WG_CONF}', 'w') as f:
    f.write('\n'.join(new_lines))
"
fi

# Queue for host-side sync + try direct
echo "wg set wg0 peer ${CLIENT_PUBKEY} allowed-ips ${NEW_ALLOWED}" >> "${PENDING}" 2>/dev/null || true
wg set wg0 peer "${CLIENT_PUBKEY}" allowed-ips "${NEW_ALLOWED}" 2>/dev/null || true
echo "Updated WireGuard route for ${USERNAME} -> slot ${SLOT} (${VPN_IP} + ${BOX_SUBNET})"
