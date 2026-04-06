#!/bin/bash
# Inter-user network isolation via iptables.
#
# Prevents traffic between different CTF slot subnets (10.100.X.0/24)
# while allowing each user to reach only their own box.
set -euo pipefail

# Flush existing rules in DOCKER-USER chain
iptables -F DOCKER-USER 2>/dev/null || true

# Allow established connections
iptables -I DOCKER-USER -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

# Block cross-subnet traffic between CTF networks
iptables -A DOCKER-USER -s 10.100.0.0/16 -d 10.100.0.0/16 -j DROP

# Default return
iptables -A DOCKER-USER -j RETURN

echo "iptables isolation rules applied"
