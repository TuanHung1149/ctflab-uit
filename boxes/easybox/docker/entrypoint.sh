#!/bin/bash
set -euo pipefail

# Inject per-instance flags from platform
if [ -n "${FLAGS_JSON:-}" ]; then
    python3 -c "
import json, os
flags = json.loads(os.environ['FLAGS_JSON'])
if 'FLAG01' in flags:
    open('/home/hacker/user.txt','w').write(flags['FLAG01']+'\n')
if 'FLAG02' in flags:
    open('/root/root.txt','w').write(flags['FLAG02']+'\n')
" 2>/dev/null || true
fi

# Set passwords
echo "hacker:hacker123" | chpasswd

exec /usr/bin/supervisord -n -c /etc/supervisor/supervisord.conf
