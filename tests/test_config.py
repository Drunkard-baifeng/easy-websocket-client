from __future__ import annotations

import unittest

from easy_websocket import (
    ApplicationHeartbeatConfig,
    AsyncWebSocketClient,
    ProxyConfig,
    SyncWebSocketClient,
    bytes_from_hex,
    bytes_to_hex,
    normalize_proxy,
)


class ProxyConfigTest(unittest.TestCase):
    def test_default_http_proxy(self) -> None:
        self.assertEqual(ProxyConfig("127.0.0.1:7890").to_url(), "http://127.0.0.1:7890")

    def test_socks5_proxy_with_auth(self) -> None:
        proxy = ProxyConfig(
            "127.0.0.1:1080",
            type="socks5",
            username="user",
            password="pass",
        )
        self.assertEqual(proxy.to_url(), "socks5://user:pass@127.0.0.1:1080")

    def test_full_proxy_url_wins(self) -> None:
        self.assertEqual(
            ProxyConfig("socks5://user:pass@127.0.0.1:1080").to_url(),
            "socks5://user:pass@127.0.0.1:1080",
        )

    def test_mapping_proxy(self) -> None:
        self.assertEqual(
            normalize_proxy({"ip": "127.0.0.1", "port": 1080, "type": "socks5h"}),
            "socks5h://127.0.0.1:1080",
        )

    def test_system_proxy_flag(self) -> None:
        self.assertIs(normalize_proxy(True), True)
        self.assertIsNone(normalize_proxy(None))
        self.assertIsNone(normalize_proxy(False))

    def test_invalid_proxy_type(self) -> None:
        with self.assertRaises(ValueError):
            ProxyConfig("127.0.0.1:7890", type="ftp").to_url()

    def test_hex_helpers(self) -> None:
        self.assertEqual(bytes_from_hex("0x0a ff:12-34"), b"\x0a\xff\x12\x34")
        self.assertEqual(bytes_to_hex(b"\x0a\xff\x12", separator=" ", uppercase=True), "0A FF 12")

    def test_application_heartbeat_cannot_be_json_and_hex(self) -> None:
        with self.assertRaises(ValueError):
            ApplicationHeartbeatConfig(enabled=True, as_json=True, as_hex=True)

    def test_clients_build_proxy_and_heartbeat_config(self) -> None:
        sync_client = SyncWebSocketClient(
            "ws://example.test/ws",
            proxy="127.0.0.1:1080",
            proxy_type="socks5",
            heartbeat=False,
        )
        async_client = AsyncWebSocketClient(
            "ws://example.test/ws",
            proxy="127.0.0.1:7890",
            proxy_type="https",
            heartbeat_interval=None,
        )

        self.assertEqual(sync_client.proxy_url, "socks5://127.0.0.1:1080")
        self.assertEqual(async_client.proxy_url, "https://127.0.0.1:7890")
        self.assertFalse(sync_client.heartbeat.enabled)
        self.assertFalse(async_client.heartbeat.enabled)


if __name__ == "__main__":
    unittest.main()
