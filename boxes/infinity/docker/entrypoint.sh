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

# Setup command logging for admin monitoring
LOG="/var/log/ctflab_cmds.log"
touch "$LOG" && chmod 622 "$LOG"

# Remove bash_history -> /dev/null symlinks, enable real history
for user_home in /home/taylor /home/brown /home/john /root; do
    rm -f "${user_home}/.bash_history" 2>/dev/null || true
    touch "${user_home}/.bash_history" 2>/dev/null || true
done

# Logging via DEBUG trap (fires BEFORE each command, works in interactive SSH)
cat >> /etc/bash.bashrc << 'CMDLOG'
_ctflab_log() {
    local cmd="$(history 1 | sed 's/^ *[0-9]* *//')"
    [ -n "$cmd" ] && printf '%s %s %s\n' "$(date +%H:%M:%S)" "$(whoami)" "$cmd" >> /var/log/ctflab_cmds.log 2>/dev/null
}
trap '_ctflab_log' DEBUG
export HISTSIZE=1000
export HISTFILESIZE=2000
shopt -s histappend
CMDLOG

# SECURITY: Clear sensitive env vars then exec supervisord via env -i
# This ensures FLAGS_JSON and SSH_PASSWORD are NOT visible via /proc/1/environ
exec env -i PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
    HOME="/root" TERM="${TERM:-xterm}" LANG="${LANG:-C.UTF-8}" \
    /usr/bin/supervisord -n -c /etc/supervisor/supervisord.conf
