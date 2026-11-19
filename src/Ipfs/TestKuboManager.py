"""Tests for the optional Kubo integration policy."""
import unittest

from Ipfs.KuboManager import KuboManager


class KuboManagerTests(unittest.TestCase):
    def test_disabled_is_inert(self):
        manager = KuboManager()
        self.assertIsNone(manager.start())

    def test_external_requires_loopback_http(self):
        manager = KuboManager(mode="external", rpc_url="http://127.0.0.1:5001")
        self.assertEqual(manager.start(), "http://127.0.0.1:5001")
        for url in ("http://192.168.1.10:5001", "https://127.0.0.1:5001",
                    "http://example.com:5001", "http://localhost"):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    KuboManager(mode="external", rpc_url=url).start()

    def test_managed_fails_closed(self):
        with self.assertRaises(NotImplementedError):
            KuboManager(mode="managed").start()

    def test_invalid_mode_rejected(self):
        with self.assertRaises(ValueError):
            KuboManager(mode="surprise")


if __name__ == "__main__":
    unittest.main()
