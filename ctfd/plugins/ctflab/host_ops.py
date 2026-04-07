"""Host-side VPN and firewall helpers for CTFLab.

These helpers execute networking commands in the host network namespace.
The CTFd container joins the host PID namespace, so ``nsenter --target 1``
can safely reach the host net namespace while keeping the container's mount
namespace (which still contains the mounted repo scripts and /etc/openvpn).
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
    use_host_netns: bool = False,
) -> subprocess.CompletedProcess[str]:
    if use_host_netns:
        cmd = ["nsenter", "--target", "1", "--net", "--"] + cmd

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


def ensure_user_vpn(username: str, server_ip: str) -> str:
    """Create a reusable per-user .ovpn file if needed and return its path."""
    _validate_name(username, "username")

    for ovpn_path in [
        f"/vpn-configs/{username}.ovpn",
        f"/opt/ctflab-uit/vpn-configs/{username}.ovpn",
    ]:
        if os.path.isfile(ovpn_path):
            return ovpn_path

    script = None
    for candidate in [
        "/scripts/setup-vpn-user.sh",
        "/opt/ctflab-uit/scripts/setup-vpn-user.sh",
    ]:
        if os.path.isfile(candidate):
            script = candidate
            break

    if not script:
        raise RuntimeError("setup-vpn-user.sh not found")

    _run(["bash", script, username, server_ip], timeout=60)

    for ovpn_path in [
        f"/vpn-configs/{username}.ovpn",
        f"/opt/ctflab-uit/vpn-configs/{username}.ovpn",
    ]:
        if os.path.isfile(ovpn_path):
            return ovpn_path

    raise RuntimeError(f"VPN config was not generated for {username}")


def update_vpn_route(username: str, slot: int | None) -> None:
    """Update the OpenVPN CCD entry for a user."""
    _validate_name(username, "username")

    script = None
    for candidate in [
        "/scripts/update-vpn-route.sh",
        "/opt/ctflab-uit/scripts/update-vpn-route.sh",
    ]:
        if os.path.isfile(candidate):
            script = candidate
            break

    if not script:
        raise RuntimeError("update-vpn-route.sh not found")

    action = str(slot) if slot is not None else "remove"
    _run(["bash", script, username, action], timeout=15)


def rebuild_network_isolation() -> None:
    """Rebuild host firewall rules for VPN <-> box access."""
    script = "/opt/ctflab-uit/fix-vpn-routing.sh"
    if not os.path.isfile(script):
        raise RuntimeError("fix-vpn-routing.sh not found")

    _run(["bash", script], timeout=30, use_host_netns=False)

