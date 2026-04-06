#!/usr/bin/env bash

set -euo pipefail

/root/infinity/docker/reset-state.sh

exec /usr/bin/supervisord -n -c /etc/supervisor/supervisord.conf
