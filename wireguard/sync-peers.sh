#!/bin/bash
set -euo pipefail

# Sync WireGuard running config with wg0.conf (peers only).
# Called by cron every 30s or by fix-vpn-routing.sh
# Runs on the HOST (not inside container).

WG_DIR="/etc/wireguard"
CONF="${WG_DIR}/wg0.conf"
PENDING="${WG_DIR}/pending-ops"

if [ ! -f "$CONF" ]; then
    exit 0
fi

# Process any pending operations
if [ -f "$PENDING" ] && [ -s "$PENDING" ]; then
    while IFS= read -r line; do
        [ -z "$line" ] && continue
        eval "$line" 2>/dev/null || true
    done < "$PENDING"
    : > "$PENDING"
fi

# Sync peers from config file to running interface
# wg-quick strip removes Interface section, keeping only Peer sections
if command -v wg-quick &>/dev/null; then
    wg syncconf wg0 <(wg-quick strip wg0) 2>/dev/null || true
fi
