"""Optional Kubo/IPFS integration lifecycle for ZirohNeth.

This module deliberately keeps IPFS disabled by default and does not download
or start third-party executables until a managed backend is implemented with
an audited, version-pinned checksum manifest.
"""
from __future__ import annotations

import logging
import os
import socket
import subprocess
from pathlib import Path
from typing import Optional

LOG = logging.getLogger("Ipfs.KuboManager")

VALID_MODES = ("disabled", "external", "managed")
DEFAULT_RPC_URL = "http://127.0.0.1:5001"


class KuboManager:
    """Minimal optional Kubo lifecycle adapter.

    * disabled: no process discovery, networking, or daemon startup.
    * external: connect only to a user-configured loopback RPC endpoint.
    * managed: reserved; fail closed until a checksum manifest is shipped.

    This class does not expose RPC beyond localhost and never launches a binary
    downloaded without verified provenance.
    """

    def __init__(self, mode: str = "disabled", rpc_url: str = DEFAULT_RPC_URL,
                 binary_path: Optional[str] = None, data_dir: Optional[str] = None):
        if mode not in VALID_MODES:
            raise ValueError("IPFS mode must be one of: " + ", ".join(VALID_MODES))
        self.mode = mode
        self.rpc_url = rpc_url
        self.binary_path = binary_path
        self.data_dir = Path(data_dir).expanduser() if data_dir else None
        self.process = None

    @staticmethod
    def _is_loopback_url(url: str) -> bool:
        # Restrict RPC to localhost addresses; avoid DNS rebinding and remote hosts.
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if parsed.scheme != "http" or parsed.port is None:
            return False
        host = parsed.hostname
        if not host:
            return False
        if host.lower() == "localhost":
            return True
        try:
            return ipaddress.ip_address(host).is_loopback
        except ValueError:
            return False

    def validate_rpc(self) -> None:
        import ipaddress
        if not self._is_loopback_url(self.rpc_url):
            raise ValueError("Kubo RPC must use HTTP on a loopback host (127.0.0.1, ::1, or localhost)")

    def start(self):
        """Start or attach according to configured mode; managed mode is fail-closed."""
        if self.mode == "disabled":
            LOG.info("IPFS integration disabled")
            return None
        if self.mode == "managed":
            raise NotImplementedError(
                "Managed Kubo downloads are disabled until a pinned release/checksum manifest is verified."
            )
        self.validate_rpc()
        LOG.info("External Kubo configured at loopback RPC %s", self.rpc_url)
        return self.rpc_url

    def stop(self):
        """Only stop a process launched by this manager; external Kubo is never stopped."""
        if self.process is None:
            return
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        self.process = None
