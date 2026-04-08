"""Docker management utilities for CTFLab instances."""

import json
import secrets
import string

import docker
from docker.types import IPAMConfig, IPAMPool

SUBNET_PREFIX = "10.100"


def generate_ssh_password(length=16):
    """Generate a random SSH password for the box."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


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
            Tuple of (container_id, network_id, container_ip, ssh_password).
        """
        network_name = f"ctflab_slot_{slot}"
        subnet = f"{SUBNET_PREFIX}.{slot}.0/24"
        gateway = f"{SUBNET_PREFIX}.{slot}.1"
        container_ip = f"{SUBNET_PREFIX}.{slot}.2"
        ssh_password = generate_ssh_password()

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

        environment = {
            "FLAGS_JSON": json.dumps(flags),
            "SSH_PASSWORD": ssh_password,
        }
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

        return container.id, network.id, container_ip, ssh_password

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

    def exec_in_container(self, container_name, cmd):
        """Execute a command inside a running container and return stdout."""
        c = self.client.containers.get(container_name)
        result = c.exec_run(cmd)
        return result.output.decode("utf-8", errors="replace")
