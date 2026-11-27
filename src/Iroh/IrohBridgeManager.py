"""Supervised JSONL client for the native ZirohNeth Iroh bridge."""
import json
import logging
import os
import shutil
from pathlib import Path

import gevent.subprocess
from gevent.lock import Semaphore

from Config import config


LOG = logging.getLogger("IrohBridge")
PROTOCOL_VERSION = 1


class IrohBridgeError(RuntimeError):
    """Raised when the native bridge is missing or rejects a request."""


class IrohBridgeManager:
    """Own one persistent sidecar process for the lifetime of the Python node."""

    _instance = None
    _instance_lock = Semaphore(1)

    @classmethod
    def instance(cls):
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self, executable=None, data_dir=None):
        self.executable = executable
        self.data_dir = Path(data_dir or config.data_dir).expanduser().resolve()
        self.process = None
        self.stderr_file = None
        self.lock = Semaphore(1)
        self.request_id = 0

    def resolve_executable(self):
        configured = (
            self.executable
            or os.environ.get("ZIROHNETH_IROH_BRIDGE")
            or shutil.which("zirohneth-iroh-bridge")
        )
        if not configured:
            raise IrohBridgeError(
                "zirohneth-iroh-bridge was not found; install the Rust sidecar "
                "or set ZIROHNETH_IROH_BRIDGE"
            )

        candidate = Path(configured).expanduser()
        if candidate.is_absolute() or candidate.parent != Path("."):
            resolved = candidate.resolve()
            if not resolved.is_file():
                raise IrohBridgeError("Configured Iroh bridge is not a regular file")
            if os.name != "nt" and not os.access(str(resolved), os.X_OK):
                raise IrohBridgeError("Configured Iroh bridge is not executable")
            return str(resolved)

        resolved = shutil.which(str(candidate))
        if not resolved:
            raise IrohBridgeError("Configured Iroh bridge executable was not found")
        return resolved

    def _start_locked(self):
        if self.process is not None and self.process.poll() is None:
            return

        self._close_handles()
        binary = self.resolve_executable()
        Path(config.log_dir).mkdir(parents=True, exist_ok=True)
        self.stderr_file = open(Path(config.log_dir) / "iroh-bridge.log", "a", encoding="utf-8")
        try:
            self.process = gevent.subprocess.Popen(
                [binary, "--data-dir", str(self.data_dir)],
                stdin=gevent.subprocess.PIPE,
                stdout=gevent.subprocess.PIPE,
                stderr=self.stderr_file,
                text=True,
                encoding="utf-8",
                bufsize=1,
            )
            self._request_locked("health", {})
        except Exception:
            self._terminate_locked()
            raise

    def _request_locked(self, operation, args):
        if self.process is None or self.process.poll() is not None:
            raise IrohBridgeError("Iroh bridge process is not running")

        self.request_id += 1
        request_id = self.request_id
        request = {
            "protocol_version": PROTOCOL_VERSION,
            "request_id": request_id,
            "op": operation,
            "args": args,
        }
        try:
            self.process.stdin.write(json.dumps(request, separators=(",", ":")) + "\n")
            self.process.stdin.flush()
            line = self.process.stdout.readline()
        except Exception as err:
            raise IrohBridgeError("Iroh bridge IPC failed: %s" % err) from err

        if not line:
            raise IrohBridgeError("Iroh bridge closed its JSONL response stream")
        if len(line) > 65536:
            raise IrohBridgeError("Iroh bridge response exceeded 64 KiB")
        try:
            response = json.loads(line)
        except ValueError as err:
            raise IrohBridgeError("Iroh bridge returned invalid JSON: %s" % err) from err

        if response.get("protocol_version") != PROTOCOL_VERSION:
            raise IrohBridgeError("Iroh bridge protocol version mismatch")
        if response.get("request_id") != request_id:
            raise IrohBridgeError("Iroh bridge response id mismatch")
        if not response.get("ok"):
            raise IrohBridgeError(response.get("error") or "Iroh bridge request failed")
        return response.get("result") or {}

    def request(self, operation, args=None):
        with self.lock:
            self._start_locked()
            return self._request_locked(operation, args or {})

    def node_addr(self):
        return self.request("node_addr")

    def add_file(self, path):
        return self.request("blob.add", {"path": str(Path(path).resolve())})

    def fetch_file(self, node_addr, content_hash, destination):
        return self.request(
            "blob.fetch",
            {
                "node_addr": node_addr,
                "hash": content_hash,
                "destination": str(Path(destination).resolve()),
            },
        )

    def _terminate_locked(self):
        process = self.process
        self.process = None
        if process is not None:
            try:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass
        self._close_handles()

    def _close_handles(self):
        if self.stderr_file is not None:
            try:
                self.stderr_file.close()
            except Exception:
                pass
            self.stderr_file = None

    def close(self):
        with self.lock:
            if self.process is not None and self.process.poll() is None:
                try:
                    self._request_locked("shutdown", {})
                except Exception as err:
                    LOG.debug("Iroh bridge shutdown request failed: %s", err)
            self._terminate_locked()


__all__ = ["IrohBridgeError", "IrohBridgeManager"]
