from __future__ import annotations

import asyncio
import json
import unittest
from threading import Thread

from websockets.asyncio.server import serve as async_serve
from websockets.sync.server import serve as sync_serve

from easy_websocket import AsyncWebSocketClient, SyncWebSocketClient


class ClientIntegrationTest(unittest.TestCase):
    def test_sync_echo_round_trip(self) -> None:
        def echo(connection):
            for message in connection:
                connection.send(message)

        with sync_serve(echo, "127.0.0.1", 0) as server:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            port = server.socket.getsockname()[1]

            with SyncWebSocketClient(
                f"ws://127.0.0.1:{port}",
                proxy=None,
                heartbeat_interval=1,
                heartbeat_timeout=1,
            ) as ws:
                self.assertEqual(ws.request("hello", timeout=2), "hello")

            server.shutdown()
            thread.join(timeout=2)

    def test_sync_hex_round_trip(self) -> None:
        def echo(connection):
            for message in connection:
                self.assertIsInstance(message, bytes)
                connection.send(message)

        with sync_serve(echo, "127.0.0.1", 0) as server:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            port = server.socket.getsockname()[1]

            with SyncWebSocketClient(f"ws://127.0.0.1:{port}", proxy=None) as ws:
                self.assertEqual(ws.request_hex("0x0a ff 12", timeout=2), "0aff12")
                self.assertEqual(ws.request_hex("0a-ff-12", timeout=2, separator=" "), "0a ff 12")

            server.shutdown()
            thread.join(timeout=2)

    def test_sync_application_heartbeat(self) -> None:
        messages: list[str] = []

        def collect(connection):
            for message in connection:
                messages.append(message)

        with sync_serve(collect, "127.0.0.1", 0) as server:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            port = server.socket.getsockname()[1]

            with SyncWebSocketClient(
                f"ws://127.0.0.1:{port}",
                proxy=None,
                app_heartbeat=True,
                app_heartbeat_message="ping",
                app_heartbeat_interval=0.05,
                app_heartbeat_immediate=True,
            ):
                self._wait_for(lambda: len(messages) >= 2)

            server.shutdown()
            thread.join(timeout=2)

        self.assertGreaterEqual(messages.count("ping"), 2)

    def test_sync_application_heartbeat_hex(self) -> None:
        messages: list[bytes] = []

        def collect(connection):
            for message in connection:
                messages.append(message)

        with sync_serve(collect, "127.0.0.1", 0) as server:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            port = server.socket.getsockname()[1]

            with SyncWebSocketClient(
                f"ws://127.0.0.1:{port}",
                proxy=None,
                app_heartbeat=True,
                app_heartbeat_message="0a ff 12",
                app_heartbeat_hex=True,
                app_heartbeat_interval=0.05,
                app_heartbeat_immediate=True,
            ):
                self._wait_for(lambda: len(messages) >= 2)

            server.shutdown()
            thread.join(timeout=2)

        self.assertGreaterEqual(messages.count(bytes.fromhex("0aff12")), 2)


    def test_async_echo_round_trip(self) -> None:
        async def scenario() -> None:
            async def echo(connection):
                async for message in connection:
                    await connection.send(message)

            async with async_serve(echo, "127.0.0.1", 0) as server:
                port = server.sockets[0].getsockname()[1]
                async with AsyncWebSocketClient(
                    f"ws://127.0.0.1:{port}",
                    proxy=None,
                    heartbeat_interval=1,
                    heartbeat_timeout=1,
                ) as ws:
                    self.assertEqual(await ws.request("hello", timeout=2), "hello")

        asyncio.run(scenario())

    def test_async_hex_round_trip(self) -> None:
        async def scenario() -> None:
            async def echo(connection):
                async for message in connection:
                    self.assertIsInstance(message, bytes)
                    await connection.send(message)

            async with async_serve(echo, "127.0.0.1", 0) as server:
                port = server.sockets[0].getsockname()[1]
                async with AsyncWebSocketClient(f"ws://127.0.0.1:{port}", proxy=None) as ws:
                    self.assertEqual(await ws.request_hex("0x0a ff 12", timeout=2), "0aff12")
                    self.assertEqual(
                        await ws.request_hex("0a:ff:12", timeout=2, uppercase=True),
                        "0AFF12",
                    )

        asyncio.run(scenario())

    def test_async_application_heartbeat_json(self) -> None:
        async def scenario() -> list[str]:
            messages: list[str] = []

            async def collect(connection):
                async for message in connection:
                    messages.append(message)

            async with async_serve(collect, "127.0.0.1", 0) as server:
                port = server.sockets[0].getsockname()[1]
                async with AsyncWebSocketClient(
                    f"ws://127.0.0.1:{port}",
                    proxy=None,
                    app_heartbeat=True,
                    app_heartbeat_message={"type": "ping"},
                    app_heartbeat_interval=0.05,
                    app_heartbeat_immediate=True,
                ):
                    await self._async_wait_for(lambda: len(messages) >= 2)
                return messages

        messages = asyncio.run(scenario())
        decoded = [json.loads(message) for message in messages]
        self.assertGreaterEqual(decoded.count({"type": "ping"}), 2)

    def _wait_for(self, predicate, timeout: float = 2.0) -> None:
        import time

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(0.01)
        self.fail("condition was not met before timeout")

    async def _async_wait_for(self, predicate, timeout: float = 2.0) -> None:
        deadline = asyncio.get_running_loop().time() + timeout
        while asyncio.get_running_loop().time() < deadline:
            if predicate():
                return
            await asyncio.sleep(0.01)
        self.fail("condition was not met before timeout")
