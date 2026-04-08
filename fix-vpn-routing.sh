#!/bin/bash
set -euo pipefail

# Docker's isolation chains often block wg0 -> bridge traffic for per-slot
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

# INPUT chain rules (host-only, skip in container where wg0 doesn't exist)
if ip link show wg0 &>/dev/null; then
    # Block VPN users from accessing Docker bridge gateway IPs
    iptables -C INPUT -s 10.200.0.0/24 -d 10.100.0.0/16 -j DROP 2>/dev/null || \
    iptables -I INPUT 1 -s 10.200.0.0/24 -d 10.100.0.0/16 -j DROP

    # Block SSH from VPN users and boxes
    iptables -C INPUT -s 10.200.0.0/24 -p tcp --dport 22 -j DROP 2>/dev/null || \
    iptables -I INPUT 1 -s 10.200.0.0/24 -p tcp --dport 22 -j DROP
    iptables -C INPUT -s 10.100.0.0/16 -p tcp --dport 22 -j DROP 2>/dev/null || \
    iptables -I INPUT 1 -s 10.100.0.0/16 -p tcp --dport 22 -j DROP

    # Block boxes from reaching ANY host service
    iptables -C INPUT -s 10.100.0.0/16 -j DROP 2>/dev/null || \
    iptables -A INPUT -s 10.100.0.0/16 -j DROP

    # Block wg0-to-wg0 forwarding (prevent VPN client-to-client)
    iptables -C FORWARD -i wg0 -o wg0 -j DROP 2>/dev/null || \
    iptables -I FORWARD 2 -i wg0 -o wg0 -j DROP
fi

iptables -N CTFLAB_ISOLATION 2>/dev/null || true
iptables -F CTFLAB_ISOLATION
iptables -D FORWARD -j CTFLAB_ISOLATION 2>/dev/null || true
iptables -I FORWARD 1 -j CTFLAB_ISOLATION

iptables -A CTFLAB_ISOLATION -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables -A CTFLAB_ISOLATION -s 10.200.0.1 -d 10.200.0.0/24 -j ACCEPT
iptables -A CTFLAB_ISOLATION -s 10.200.0.0/24 -d 10.200.0.1 -j ACCEPT
iptables -A CTFLAB_ISOLATION -s 10.200.0.0/24 -d 10.200.0.0/24 -j DROP
iptables -A CTFLAB_ISOLATION -s 10.100.0.0/16 -d 10.100.0.0/16 -j DROP

# Block boxes from reaching cloud metadata, host network, and other VPN users
iptables -A CTFLAB_ISOLATION -s 10.100.0.0/16 -d 169.254.169.254 -j DROP
iptables -A CTFLAB_ISOLATION -s 10.100.0.0/16 -d 10.200.0.0/24 -j DROP
iptables -A CTFLAB_ISOLATION -s 10.100.0.0/16 -d 172.16.0.0/12 -j DROP

# For each running container, find which user owns it via WireGuard client directories.
# Each client dir has a slot file and public key. We match against the container's slot label.
DOCKER_FMT='{{index .Config.Labels "ctflab.slot"}}'
WG_CLIENTS="/etc/wireguard/clients"

for container in $(docker ps --filter "label=ctflab.managed=true" --format "{{.Names}}" 2>/dev/null); do
    docker_slot=$(docker inspect "$container" --format "$DOCKER_FMT" 2>/dev/null || true)
    if [ -z "$docker_slot" ] || ! [ "$docker_slot" -gt 0 ] 2>/dev/null; then
        continue
    fi

    docker_subnet="10.100.${docker_slot}.0/24"

    # Find the user whose WG AllowedIPs includes this Docker subnet.
    # Read from wg0.conf since wg command may not be available in container.
    if [ -d "$WG_CLIENTS" ]; then
        for client_dir in "${WG_CLIENTS}"/*/; do
            [ -d "$client_dir" ] || continue
            slot_file="${client_dir}/slot"
            [ -f "$slot_file" ] || continue
            client_wg_slot=$(cat "$slot_file" 2>/dev/null || true)
            [ -n "$client_wg_slot" ] || continue
            client_vpn_ip="10.200.0.$((client_wg_slot + 1))"

            # Check if wg0.conf has this peer with the Docker subnet
            pubkey_file="${client_dir}/public.key"
            [ -f "$pubkey_file" ] || continue
            pubkey=$(cat "$pubkey_file")

            # Check if this peer's AllowedIPs in wg0.conf include the docker subnet
            if grep -q "${pubkey}" /etc/wireguard/wg0.conf 2>/dev/null; then
                if grep -A1 "${pubkey}" /etc/wireguard/wg0.conf 2>/dev/null | grep -q "10.100.${docker_slot}.0/24"; then
                    iptables -A CTFLAB_ISOLATION -s "$client_vpn_ip" -d "$docker_subnet" -j ACCEPT
                    iptables -A CTFLAB_ISOLATION -s "$docker_subnet" -d "$client_vpn_ip" -j ACCEPT
                    break
                fi
            fi
        done
    fi
done

iptables -A CTFLAB_ISOLATION -s 10.200.0.0/24 -d 10.100.0.0/16 -j DROP

# Block boxes from reaching internet (only allow their own subnet + VPN server)
iptables -A CTFLAB_ISOLATION -s 10.100.0.0/16 -j DROP

# Catch-all: block VPN users from going anywhere else (prevent open proxy)
iptables -A CTFLAB_ISOLATION -s 10.200.0.0/24 -j DROP

iptables -A CTFLAB_ISOLATION -j RETURN

# WireGuard sync (only works on host, silently skipped in container)
# Wrapped in subshell with set +e because wg commands fail inside Docker container
(
    set +e
    WG_DIR="/etc/wireguard"
    PENDING="${WG_DIR}/pending-ops"

    # Sync base config first
    if [ -f "${WG_DIR}/wg0.conf" ] && command -v wg-quick &>/dev/null; then
        wg syncconf wg0 <(wg-quick strip wg0) 2>/dev/null
    fi

    # Then apply pending operations (overrides for route updates)
    if [ -f "$PENDING" ] && [ -s "$PENDING" ]; then
        while IFS= read -r line; do
            [ -z "$line" ] && continue
            eval "$line" 2>/dev/null
        done < "$PENDING"
        : > "$PENDING"
    fi
) 2>/dev/null || true
