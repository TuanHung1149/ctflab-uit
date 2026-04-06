#!/usr/bin/env bash

set -euo pipefail

# Inject per-instance random flags (from FLAGS_JSON env var set by platform)
if [ -x /root/infinity/docker/inject-flags.sh ]; then
    /root/infinity/docker/inject-flags.sh
fi

/root/infinity/docker/reset-state.sh

exec /usr/bin/supervisord -n -c /etc/supervisor/supervisord.conf
