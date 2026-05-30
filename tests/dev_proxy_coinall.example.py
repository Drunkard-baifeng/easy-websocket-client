from __future__ import annotations

import os
import unittest

from easy_websocket import SyncWebSocketClient

PROXY = os.getenv("EASY_WS_PROXY", "127.0.0.1:1080")
PROXY_TYPE = os.getenv("EASY_WS_PROXY_TYPE", "socks5")
PROXY_USERNAME = os.getenv("EASY_WS_PROXY_USERNAME")
PROXY_PASSWORD = os.getenv("EASY_WS_PROXY_PASSWORD")

COINALL_URL = "wss://wsdexpri.coinall.ltd/ws/v5/iprivate"
ORIGIN = "chrome-extension://mcohilncbfahbmgdjkbpemcciiolgcge"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/148.0.0.0 Safari/537.36"
)
HEADERS = {
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}


class CoinAllProxyDevelopmentTest(unittest.TestCase):
    def test_sync_connect_coinall_with_proxy(self) -> None:
        with SyncWebSocketClient(
            COINALL_URL,
            proxy=PROXY,
            proxy_type=PROXY_TYPE,
            proxy_username=PROXY_USERNAME,
            proxy_password=PROXY_PASSWORD,
            headers=HEADERS,
            origin=ORIGIN,
            user_agent_header=USER_AGENT,
            open_timeout=20,
            close_timeout=5,
            heartbeat=True,
            heartbeat_interval=20,
            heartbeat_timeout=10,
        ) as ws:
            self.assertTrue(ws.connected)
