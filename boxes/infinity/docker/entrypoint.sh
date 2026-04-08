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

# SECURITY: Clear sensitive env vars then exec supervisord via env -i
# This ensures FLAGS_JSON and SSH_PASSWORD are NOT visible via /proc/1/environ
exec env -i PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
    HOME="/root" TERM="${TERM:-xterm}" LANG="${LANG:-C.UTF-8}" \
    /usr/bin/supervisord -n -c /etc/supervisor/supervisord.conf
