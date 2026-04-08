#!/usr/bin/env bash

set -euo pipefail

# Set SSH password from environment (random per instance) or fallback
SSH_PASS="${SSH_PASSWORD:-$(openssl rand -base64 12)}"
echo "taylor:${SSH_PASS}" | chpasswd
echo "brown:$(openssl rand -base64 16)" | chpasswd
echo "john:$(openssl rand -base64 16)" | chpasswd

# Inject per-instance random flags (from FLAGS_JSON env var set by platform)
if [ -x /root/infinity/docker/inject-flags.sh ]; then
    /root/infinity/docker/inject-flags.sh
fi

/root/infinity/docker/reset-state.sh

exec /usr/bin/supervisord -n -c /etc/supervisor/supervisord.conf
