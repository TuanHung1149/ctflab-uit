#!/bin/bash
set -euo pipefail

# Docker's isolation chains often block tun0 -> bridge traffic for per-slot
# networks. We flatten those rules, then rebuild explicit CTFLab policies.
for h in $(nft -a list chain ip raw PREROUTING 2>/dev/null | grep "10.100.*drop" | grep -oP "handle \K\d+"); do
    nft delete rule ip raw PREROUTING handle "$h" 2>/dev/null || true
done
for h in $(nft -a list chain ip filter FORWARD 2>/dev/null | grep "10.100.*drop" | grep -oP "handle \K\d+"); do
    nft delete rule ip filter FORWARD handle "$h" 2>/dev/null || true
done
nft flush chain ip filter DOCKER-ISOLATION-STAGE-2 2>/dev/null || true
nft add rule ip filter DOCKER-ISOLATION-STAGE-2 return 2>/dev/null || true

for i in /proc/sys/net/ipv4/conf/*; do
    iface=$(basename "$i")
    sysctl -qw "net.ipv4.conf.${iface}.rp_filter=0" 2>/dev/null || true
done

iptables -t nat -C POSTROUTING -s 10.200.0.0/24 -j MASQUERADE 2>/dev/null || \
iptables -t nat -A POSTROUTING -s 10.200.0.0/24 -j MASQUERADE

iptables -N CTFLAB_ISOLATION 2>/dev/null || true
iptables -F CTFLAB_ISOLATION
iptables -D FORWARD -j CTFLAB_ISOLATION 2>/dev/null || true
iptables -I FORWARD 1 -j CTFLAB_ISOLATION

iptables -A CTFLAB_ISOLATION -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables -A CTFLAB_ISOLATION -s 10.200.0.1 -d 10.200.0.0/24 -j ACCEPT
iptables -A CTFLAB_ISOLATION -s 10.200.0.0/24 -d 10.200.0.1 -j ACCEPT
iptables -A CTFLAB_ISOLATION -s 10.200.0.0/24 -d 10.200.0.0/24 -j DROP
iptables -A CTFLAB_ISOLATION -s 10.100.0.0/16 -d 10.100.0.0/16 -j DROP

DOCKER_FMT='{{index .Config.Labels "ctflab.slot"}}'
for container in $(docker ps --filter "label=ctflab.managed=true" --format "{{.Names}}" 2>/dev/null); do
    slot=$(docker inspect "$container" --format "$DOCKER_FMT" 2>/dev/null || true)
    if [ -n "$slot" ] && [ "$slot" -gt 0 ] 2>/dev/null; then
        vpn_ip="10.200.0.$((slot + 1))"
        iptables -A CTFLAB_ISOLATION -s "$vpn_ip" -d "10.100.${slot}.0/24" -j ACCEPT
        iptables -A CTFLAB_ISOLATION -s "10.100.${slot}.0/24" -d "$vpn_ip" -j ACCEPT
    fi
done

iptables -A CTFLAB_ISOLATION -s 10.200.0.0/24 -d 10.100.0.0/16 -j DROP
iptables -A CTFLAB_ISOLATION -j RETURN
