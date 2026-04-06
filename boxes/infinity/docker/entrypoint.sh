#!/usr/bin/env bash

set -euo pipefail

# Ensure SSH user passwords are set correctly on every start
echo "taylor:lekkerding" | chpasswd
echo "brown:AI56JSPUac43v7MWkXdG" | chpasswd
echo "john:S6V1frkRJLo40GKuglzp" | chpasswd

# Inject per-instance random flags (from FLAGS_JSON env var set by platform)
if [ -x /root/infinity/docker/inject-flags.sh ]; then
    /root/infinity/docker/inject-flags.sh
fi

/root/infinity/docker/reset-state.sh

exec /usr/bin/supervisord -n -c /etc/supervisor/supervisord.conf
