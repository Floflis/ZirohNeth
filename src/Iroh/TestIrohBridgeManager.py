"""Policy tests for the optional Iroh bridge adapter."""
import os
import tempfile
import unittest
from pathlib import Path

from .IrohBridgeManager import IrohBridgeManager


class TestIrohBridgeManager(unittest.TestCase):
    def test_disabled_does_not_resolve_binary(self):
        manager = IrohBridgeManager()
        self.assertIsNone(manager.start())

    def test_external_requires_bridge(self):
        manager = IrohBridgeManager(mode="external", bridge_path="missing-iroh-bridge")
        with self.assertRaises(FileNotFoundError):
            manager.resolve_bridge()

    def test_external_rejects_non_executable(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bridge"
            path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            if os.name != "nt":
                path.chmod(0o600)
                manager = IrohBridgeManager(mode="external", bridge_path=str(path))
                with self.assertRaises(PermissionError):
                    manager.resolve_bridge()

    def test_external_does_not_launch_unknown_protocol(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bridge"
            path.write_text("placeholder", encoding="utf-8")
            if os.name != "nt":
                path.chmod(0o700)
            manager = IrohBridgeManager(mode="external", bridge_path=str(path))
            with self.assertRaises(NotImplementedError):
                manager.start()


if __name__ == "__main__":
    unittest.main()
