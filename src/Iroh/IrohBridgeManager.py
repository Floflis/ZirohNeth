"""Optional Iroh bridge discovery for ZirohNeth.

Iroh is a Rust library/API, not a universal daemon with a stable generic RPC
endpoint. This adapter therefore does not pretend that an arbitrary `iroh`
binary is a compatible service. The external mode only validates a dedicated
ZirohNeth bridge executable; launching and speaking its protocol remain
disabled until the bridge contract and Rust implementation are shipped.
"""
from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Optional

LOG = logging.getLogger("Iroh.IrohBridgeManager")
VALID_MODES = ("disabled", "external")


class IrohBridgeManager:
    """Fail-closed manager for a future Rust/Iroh sidecar.

    * disabled: do not inspect or start any process.
    * external: resolve a user-installed bridge executable, but do not launch
      it until a versioned, authenticated IPC protocol is implemented.
    """

    def __init__(self, mode: str = "disabled", bridge_path: str = "iroh-bridge"):
        if mode not in VALID_MODES:
            raise ValueError("Iroh mode must be one of: " + ", ".join(VALID_MODES))
        self.mode = mode
        self.bridge_path = bridge_path
        self.process = None

    def resolve_bridge(self) -> Optional[Path]:
        """Return an absolute executable path, or None when Iroh is disabled."""
        if self.mode == "disabled":
            LOG.info("Iroh integration disabled")
            return None

        candidate = Path(self.bridge_path).expanduser()
        resolved = shutil.which(str(candidate)) if not candidate.is_absolute() else str(candidate)
        if not resolved:
            raise FileNotFoundError(
                "Iroh external mode requires an installed ZirohNeth iroh-bridge executable"
            )

        path = Path(resolved).resolve()
        if not path.is_file():
            raise FileNotFoundError("Configured Iroh bridge is not a regular file")
        if os.name != "nt" and not os.access(str(path), os.X_OK):
            raise PermissionError("Configured Iroh bridge is not executable")

        LOG.info("Found external Iroh bridge at %s", path)
        return path

    def start(self):
        """Discover the bridge only; never execute an unversioned sidecar."""
        bridge = self.resolve_bridge()
        if bridge is None:
            return None
        raise NotImplementedError(
            "Iroh bridge execution is disabled until the versioned JSONL/ALPN protocol is implemented"
        )

    def stop(self):
        """Only a future manager-owned process may be stopped."""
        if self.process is None:
            return
        if self.process.poll() is None:
            self.process.terminate()
            self.process.wait(timeout=5)
        self.process = None
