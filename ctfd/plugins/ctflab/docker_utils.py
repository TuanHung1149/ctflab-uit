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
        """Generate OpenVPN client config by calling setup-vpn-slot.sh.

        This creates the client cert, CCD entry, and .ovpn file on the host.
        Returns the .ovpn file content.
        """
        import os
        import subprocess

        server_ip = os.environ.get("OVPN_SERVER_IP", "152.42.233.178")

        # Try setup-vpn-slot.sh (creates cert + CCD + .ovpn)
        for script in [
            "/opt/ctflab-uit/scripts/setup-vpn-slot.sh",
            "/scripts/setup-vpn-slot.sh",
        ]:
            if os.path.isfile(script):
                try:
                    subprocess.run(
                        ["bash", script, str(slot), server_ip],
                        capture_output=True, text=True, timeout=30,
                    )
                except Exception:
                    pass
                break

        # Read generated .ovpn file
        for ovpn_path in [
            f"/opt/ctflab-uit/vpn-configs/slot-{slot}.ovpn",
            f"/vpn-configs/slot-{slot}.ovpn",
        ]:
            if os.path.isfile(ovpn_path):
                content = open(ovpn_path).read()
                if "BEGIN CERTIFICATE" in content:
                    return content

        # Also fix routing after creating instance
        try:
            subprocess.run(
                ["bash", "/opt/ctflab-uit/fix-vpn-routing.sh"],
                capture_output=True, timeout=10,
            )
        except Exception:
            pass

        return (
            f"# CTFLab OpenVPN Config - Slot {slot}\n"
            f"# VPN config generation failed. Contact admin.\n"
            f"# Box IP: {container_ip}\n"
        )

    def get_container_logs(self, container_name, tail=200):
        """Get last N lines of container logs."""
        try:
            c = self.client.containers.get(container_name)
            logs = c.logs(tail=tail, timestamps=True).decode("utf-8", errors="replace")
            return logs
        except docker.errors.NotFound:
            return f"Container {container_name} not found"
        except Exception as e:
            return f"Error: {str(e)}"
