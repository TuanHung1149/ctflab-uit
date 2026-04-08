"""Host-side VPN and firewall helpers for CTFLab.

WireGuard-based VPN management. The CTFd container has access to
/etc/wireguard (mounted) and /scripts (mounted) to manage WireGuard
peers and generate client configs.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess

logger = logging.getLogger(__name__)

_SAFE_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")


def _validate_name(name: str, field: str) -> None:
    if not name or not _SAFE_NAME.fullmatch(name):
        raise RuntimeError(f"Invalid {field}: {name!r}")


def _run(
    cmd: list[str],
    *,
    timeout: int = 30,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if check and result.returncode != 0:
        stderr = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(
            f"Command failed ({result.returncode}): {' '.join(cmd)}"
            + (f" :: {stderr}" if stderr else "")
        )
    return result


def _sync_wireguard() -> None:
    """Trigger host-side WireGuard peer sync.

    The sync script runs on the host and processes pending wg operations.
    We try multiple paths since the script may be in different locations.
    """
    for script in [
        "/opt/ctflab-uit/wireguard/sync-peers.sh",
        "/scripts/../wireguard/sync-peers.sh",
    ]:
        if os.path.isfile(script):
            _run(["bash", script], timeout=10, check=False)
            return


def ensure_user_vpn(username: str, server_ip: str) -> str:
    """Create a reusable per-user WireGuard .conf file if needed and return its path."""
    _validate_name(username, "username")

    # Check if config already exists
    for conf_path in [
        f"/vpn-configs/{username}.conf",
        f"/opt/ctflab-uit/vpn-configs/{username}.conf",
    ]:
        if os.path.isfile(conf_path):
            return conf_path

    # Find and run the setup script
    script = None
    for candidate in [
        "/scripts/setup-wg-user.sh",
        "/opt/ctflab-uit/scripts/setup-wg-user.sh",
    ]:
        if os.path.isfile(candidate):
            script = candidate
            break

    if not script:
        raise RuntimeError("setup-wg-user.sh not found")

    _run(["bash", script, username, server_ip], timeout=60)

    # Return the generated config path
    for conf_path in [
        f"/vpn-configs/{username}.conf",
        f"/opt/ctflab-uit/vpn-configs/{username}.conf",
    ]:
        if os.path.isfile(conf_path):
            return conf_path

    raise RuntimeError(f"WireGuard config was not generated for {username}")


def update_vpn_route(username: str, slot: int | None) -> None:
    """Update the WireGuard peer's AllowedIPs when a box starts/stops."""
    _validate_name(username, "username")

    script = None
    for candidate in [
        "/scripts/update-wg-route.sh",
        "/opt/ctflab-uit/scripts/update-wg-route.sh",
    ]:
        if os.path.isfile(candidate):
            script = candidate
            break

    if not script:
        raise RuntimeError("update-wg-route.sh not found")

    action = str(slot) if slot is not None else "remove"
    _run(["bash", script, username, action], timeout=15)


def rebuild_network_isolation() -> None:
    """Rebuild host firewall rules for VPN <-> box access and sync WireGuard peers."""
    script = "/opt/ctflab-uit/fix-vpn-routing.sh"
    if not os.path.isfile(script):
        raise RuntimeError("fix-vpn-routing.sh not found")

    _run(["bash", script], timeout=30)
    _sync_wireguard()
