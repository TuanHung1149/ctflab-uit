"""OpenVPN management service for CTFLab.

Handles:
- EasyRSA PKI initialisation (CA, server cert, DH params)
- Per-slot client certificate generation and revocation
- .ovpn config file generation with embedded certificates
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import subprocess
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

EASYRSA_DIR = Path("/etc/openvpn/easy-rsa")
PKI_DIR = EASYRSA_DIR / "pki"
OVPN_SERVER_CONF = Path("/etc/openvpn/server.conf")


class OpenVPNService:
    """Async service for managing OpenVPN client certificates and configs."""

    def __init__(self) -> None:
        self.server_ip: str = settings.OVPN_SERVER_IP
        self.server_port: int = settings.OVPN_SERVER_PORT
        self.proto: str = settings.OVPN_PROTO

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _run(
        self,
        cmd: list[str],
        cwd: str | None = None,
        env: dict[str, str] | None = None,
    ) -> str:
        """Run a subprocess command asynchronously.

        Raises:
            RuntimeError: If the command exits with a non-zero return code.
        """
        proc_env = os.environ.copy()
        if env:
            proc_env.update(env)

        result = await asyncio.to_thread(
            subprocess.run,
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            env=proc_env,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Command failed: {' '.join(cmd)}\n{result.stderr}"
            )
        return result.stdout

    @staticmethod
    def _read_file(path: Path) -> str:
        """Read and strip a text file."""
        return path.read_text().strip()

    # ------------------------------------------------------------------
    # PKI management
    # ------------------------------------------------------------------

    async def init_pki(self) -> None:
        """Initialise the PKI and CA. Safe to call repeatedly (no-op if already done)."""
        if PKI_DIR.exists():
            logger.info("PKI already initialised at %s", PKI_DIR)
            return

        easyrsa = str(EASYRSA_DIR / "easyrsa")
        env = {"EASYRSA_BATCH": "1", "EASYRSA_REQ_CN": "CTFLab-CA"}
        cwd = str(EASYRSA_DIR)

        await self._run([easyrsa, "init-pki"], cwd=cwd, env=env)
        await self._run([easyrsa, "build-ca", "nopass"], cwd=cwd, env=env)
        await self._run([easyrsa, "gen-dh"], cwd=cwd, env=env)
        await self._run(
            [easyrsa, "build-server-full", "server", "nopass"],
            cwd=cwd,
            env=env,
        )
        logger.info("PKI initialised successfully")

    # ------------------------------------------------------------------
    # Client certificate lifecycle
    # ------------------------------------------------------------------

    async def generate_client_cert(self, client_name: str) -> None:
        """Generate a client certificate via EasyRSA."""
        easyrsa = str(EASYRSA_DIR / "easyrsa")
        env = {"EASYRSA_BATCH": "1"}

        await self._run(
            [easyrsa, "build-client-full", client_name, "nopass"],
            cwd=str(EASYRSA_DIR),
            env=env,
        )
        logger.info("Generated client cert for %s", client_name)

    async def revoke_client_cert(self, client_name: str) -> None:
        """Revoke a client certificate and regenerate the CRL."""
        easyrsa = str(EASYRSA_DIR / "easyrsa")
        env = {"EASYRSA_BATCH": "1"}
        cwd = str(EASYRSA_DIR)

        try:
            await self._run([easyrsa, "revoke", client_name], cwd=cwd, env=env)
            await self._run([easyrsa, "gen-crl"], cwd=cwd, env=env)
            logger.info("Revoked client cert for %s", client_name)
        except RuntimeError:
            logger.warning(
                "Failed to revoke cert for %s (may not exist)", client_name,
            )

    # ------------------------------------------------------------------
    # Config generation
    # ------------------------------------------------------------------

    async def generate_ovpn_config(self, client_name: str, slot: int) -> str:
        """Generate a complete .ovpn config with embedded certificates.

        Uses split-tunnel routing so only the CTF subnet (10.100.{slot}.0/24)
        is routed through the VPN.
        """
        ca_cert = self._read_file(PKI_DIR / "ca.crt")
        client_cert_raw = self._read_file(PKI_DIR / "issued" / f"{client_name}.crt")
        client_key = self._read_file(PKI_DIR / "private" / f"{client_name}.key")

        # Extract only the PEM certificate block
        cert_match = re.search(
            r"(-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----)",
            client_cert_raw,
            re.DOTALL,
        )
        client_cert = cert_match.group(1) if cert_match else client_cert_raw

        config = (
            f"client\n"
            f"dev tun\n"
            f"proto {self.proto}\n"
            f"remote {self.server_ip} {self.server_port}\n"
            f"resolv-retry infinite\n"
            f"nobind\n"
            f"persist-key\n"
            f"persist-tun\n"
            f"remote-cert-tls server\n"
            f"verb 3\n"
            f"\n"
            f"# Split tunnel - only route CTF subnet through VPN\n"
            f"route-nopull\n"
            f"route 10.100.{slot}.0 255.255.255.0\n"
            f"\n"
            f"# Push DNS to box IP for domain resolution\n"
            f"dhcp-option DNS 10.100.{slot}.2\n"
            f"\n"
            f"<ca>\n"
            f"{ca_cert}\n"
            f"</ca>\n"
            f"<cert>\n"
            f"{client_cert}\n"
            f"</cert>\n"
            f"<key>\n"
            f"{client_key}\n"
            f"</key>\n"
        )
        return config

    # ------------------------------------------------------------------
    # High-level client operations
    # ------------------------------------------------------------------

    async def create_client(self, slot: int) -> str:
        """Full flow: generate certificate and return .ovpn config content."""
        client_name = f"ctflab_slot_{slot}"
        await self.generate_client_cert(client_name)
        config = await self.generate_ovpn_config(client_name, slot)
        logger.info("Created VPN client config for slot %d", slot)
        return config

    async def remove_client(self, slot: int) -> None:
        """Revoke the client certificate for a slot."""
        client_name = f"ctflab_slot_{slot}"
        await self.revoke_client_cert(client_name)
        logger.info("Removed VPN client for slot %d", slot)
