"""Full Docker lifecycle management for CTF box containers.

Responsibilities:
- Build box images from Dockerfiles
- Create isolated per-slot bridge networks (10.100.N.0/24)
- Run hardened CTF containers with resource limits
- Stop, remove, and inspect containers
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import docker
from docker.errors import NotFound
from docker.types import IPAMConfig, IPAMPool

logger = logging.getLogger(__name__)


class DockerService:
    """Async wrapper around the Docker SDK for managing CTF infrastructure."""

    def __init__(self) -> None:
        self.client: docker.DockerClient = docker.from_env()

    # ------------------------------------------------------------------
    # Image management
    # ------------------------------------------------------------------

    async def build_image(self, path: str, tag: str) -> str:
        """Build a Docker image from a box directory.

        Args:
            path: Filesystem path containing the Dockerfile.
            tag: Image tag, e.g. ``ctflab/infinity``.

        Returns:
            The built image ID.
        """
        image, logs = await asyncio.to_thread(
            self.client.images.build, path=path, tag=tag, rm=True,
        )
        for chunk in logs:
            if "stream" in chunk:
                logger.debug(chunk["stream"].rstrip())
        return image.id

    # ------------------------------------------------------------------
    # Network management
    # ------------------------------------------------------------------

    async def create_network(self, slot: int) -> tuple[str, str]:
        """Create an isolated bridge network for a slot.

        Returns:
            ``(network_id, network_name)``
        """
        network_name = f"ctflab_slot_{slot}"
        subnet = f"10.100.{slot}.0/24"
        gateway = f"10.100.{slot}.1"

        ipam = IPAMConfig(
            pool_configs=[IPAMPool(subnet=subnet, gateway=gateway)],
        )
        network = await asyncio.to_thread(
            self.client.networks.create,
            name=network_name,
            driver="bridge",
            ipam=ipam,
            labels={"ctflab.slot": str(slot), "ctflab.managed": "true"},
        )
        logger.info("Created network %s (%s) for slot %d", network_name, network.id, slot)
        return network.id, network_name

    async def remove_network(self, network_id: str) -> None:
        """Remove a Docker network by ID. Silently ignores missing networks."""
        try:
            network = await asyncio.to_thread(self.client.networks.get, network_id)
            await asyncio.to_thread(network.remove)
            logger.info("Removed network %s", network_id)
        except NotFound:
            logger.debug("Network %s already removed", network_id)

    # ------------------------------------------------------------------
    # Container management
    # ------------------------------------------------------------------

    async def run_box(
        self,
        image: str,
        slot: int,
        network_name: str,
        flags: dict[str, str],
        env_overrides: dict[str, str] | None = None,
    ) -> tuple[str, str]:
        """Run a CTF box container with hardened security settings.

        Args:
            image: Docker image name/tag.
            slot: Slot number determining the IP address.
            network_name: Name of the pre-created Docker network.
            flags: Mapping of flag prefix to flag value.
            env_overrides: Extra environment variables to inject.

        Returns:
            ``(container_id, container_ip)``
        """
        container_ip = f"10.100.{slot}.2"

        environment: dict[str, Any] = {
            "FLAGS_JSON": json.dumps(flags),
        }
        if env_overrides:
            environment.update(env_overrides)

        container = await asyncio.to_thread(
            self.client.containers.run,
            image=image,
            name=f"ctflab_box_{slot}",
            detach=True,
            network=network_name,
            # --- Resource limits ---
            mem_limit="512m",
            memswap_limit="512m",
            cpu_period=100000,
            cpu_quota=100000,   # 1.0 CPU
            pids_limit=200,
            # --- Security hardening ---
            security_opt=["no-new-privileges"],
            cap_drop=["ALL"],
            cap_add=[
                "CHOWN",
                "DAC_OVERRIDE",
                "FOWNER",
                "SETGID",
                "SETUID",
                "NET_BIND_SERVICE",
                "SYS_CHROOT",
                "KILL",
            ],
            environment=environment,
            labels={"ctflab.slot": str(slot), "ctflab.managed": "true"},
            restart_policy={"Name": "unless-stopped"},
        )
        logger.info(
            "Started container %s (image=%s, slot=%d, ip=%s)",
            container.id[:12], image, slot, container_ip,
        )
        return container.id, container_ip

    async def stop_and_remove(self, container_id: str) -> None:
        """Stop and force-remove a container. Silently ignores missing containers."""
        try:
            container = await asyncio.to_thread(
                self.client.containers.get, container_id,
            )
            await asyncio.to_thread(container.stop, timeout=10)
            await asyncio.to_thread(container.remove, force=True)
            logger.info("Stopped and removed container %s", container_id[:12])
        except NotFound:
            logger.debug("Container %s already removed", container_id[:12])

    async def exec_in_container(self, container_id: str, cmd: list[str]) -> str:
        """Execute a command inside a running container and return stdout."""
        container = await asyncio.to_thread(
            self.client.containers.get, container_id,
        )
        result = await asyncio.to_thread(container.exec_run, cmd, demux=True)
        stdout, _ = result.output
        return (stdout or b"").decode()

    async def get_status(self, container_id: str) -> str:
        """Return the container status string, or ``'not_found'``."""
        try:
            container = await asyncio.to_thread(
                self.client.containers.get, container_id,
            )
            return container.status
        except NotFound:
            return "not_found"
