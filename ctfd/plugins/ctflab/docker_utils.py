"""Docker management utilities for CTFLab instances."""

import json

import docker
from docker.types import IPAMConfig, IPAMPool

SUBNET_PREFIX = "10.100"


class DockerManager:
    """Manages Docker containers and networks for lab instances."""

    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = docker.from_env()
        return self._client

    def create_instance(self, image, slot, flags, env_overrides=None):
        """Create an isolated network and run the box container.

        Returns:
            Tuple of (container_id, network_id, container_ip).
        """
        network_name = f"ctflab_slot_{slot}"
        subnet = f"{SUBNET_PREFIX}.{slot}.0/24"
        gateway = f"{SUBNET_PREFIX}.{slot}.1"
        container_ip = f"{SUBNET_PREFIX}.{slot}.2"

        self._cleanup_slot(slot)

        ipam = IPAMConfig(
            pool_configs=[IPAMPool(subnet=subnet, gateway=gateway)]
        )
        network = self.client.networks.create(
            name=network_name,
            driver="bridge",
            ipam=ipam,
            labels={
                "ctflab.slot": str(slot),
                "ctflab.managed": "true",
            },
        )

        environment = {"FLAGS_JSON": json.dumps(flags)}
        if env_overrides:
            environment.update(env_overrides)

        container = self.client.containers.run(
            image=image,
            name=f"ctflab_box_{slot}",
            detach=True,
            network=network_name,
            mem_limit="512m",
            cpu_period=100000,
            cpu_quota=100000,
            pids_limit=200,
            security_opt=["no-new-privileges"],
            environment=environment,
            labels={
                "ctflab.slot": str(slot),
                "ctflab.managed": "true",
            },
            restart_policy={"Name": "unless-stopped"},
        )

        return container.id, network.id, container_ip

    def destroy_instance(self, container_id, network_id):
        """Stop a container and remove its network."""
        try:
            c = self.client.containers.get(container_id)
            c.stop(timeout=10)
            c.remove(force=True)
        except docker.errors.NotFound:
            pass

        try:
            n = self.client.networks.get(network_id)
            n.remove()
        except docker.errors.NotFound:
            pass

    def reset_instance(self, container_id):
        """Execute the reset script inside the container."""
        c = self.client.containers.get(container_id)
        c.exec_run(["/root/infinity/docker/reset-state.sh"])

    def _cleanup_slot(self, slot):
        """Remove any leftover container or network for a slot."""
        try:
            c = self.client.containers.get(f"ctflab_box_{slot}")
            c.remove(force=True)
        except docker.errors.NotFound:
            pass

        try:
            n = self.client.networks.get(f"ctflab_slot_{slot}")
            n.remove()
        except docker.errors.NotFound:
            pass

    def generate_vpn_config(self, slot, container_ip):
        """Generate an OpenVPN client configuration.

        In production this would use EasyRSA PKI to embed real
        certificates.  The generated template includes placeholders
        that must be filled in after running the server-side PKI setup.
        """
        return (
            f"# CTFLab OpenVPN Config - Slot {slot}\n"
            f"#\n"
            f"# SETUP REQUIRED:\n"
            f"# 1. Run openvpn/setup-server.sh on the host first\n"
            f"# 2. Generate client certs:\n"
            f"#    cd /etc/openvpn/easy-rsa && "
            f"./easyrsa build-client-full ctflab_slot_{slot} nopass\n"
            f"# 3. Replace the <ca>, <cert>, <key> sections below "
            f"with actual certs\n"
            f"#\n"
            f"# Target box IP: {container_ip}\n"
            f"# Accessible ports: 53 (DNS), 80 (HTTP), "
            f"7171 (Bot), 8338 (Maltrail)\n"
            f"\n"
            f"client\n"
            f"dev tun\n"
            f"proto udp\n"
            f"remote YOUR_SERVER_IP 1194\n"
            f"resolv-retry infinite\n"
            f"nobind\n"
            f"persist-key\n"
            f"persist-tun\n"
            f"remote-cert-tls server\n"
            f"verb 3\n"
            f"\n"
            f"# Split tunnel - only route CTF subnet through VPN\n"
            f"route-nopull\n"
            f"route {SUBNET_PREFIX}.{slot}.0 255.255.255.0\n"
            f"\n"
            f"<ca>\n"
            f"# INSERT CA CERT HERE\n"
            f"# cat /etc/openvpn/easy-rsa/pki/ca.crt\n"
            f"</ca>\n"
            f"<cert>\n"
            f"# INSERT CLIENT CERT HERE\n"
            f"# cat /etc/openvpn/easy-rsa/pki/issued/"
            f"ctflab_slot_{slot}.crt\n"
            f"</cert>\n"
            f"<key>\n"
            f"# INSERT CLIENT KEY HERE\n"
            f"# cat /etc/openvpn/easy-rsa/pki/private/"
            f"ctflab_slot_{slot}.key\n"
            f"</key>\n"
        )
