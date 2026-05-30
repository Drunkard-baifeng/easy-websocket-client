from __future__ import annotations

import asyncio
import json
from contextlib import suppress
from typing import Any, AsyncIterator, Mapping, Sequence

from .codec import bytes_from_hex, bytes_to_hex
from .exceptions import MissingDependencyError, WebSocketNotConnectedError

try:
    from websockets.asyncio.client import connect as async_connect
except ImportError as exc:
    raise MissingDependencyError(
        'Install dependencies with: pip install "websockets>=15.0" '
        '"python-socks[asyncio]>=2.4"'
    ) from exc

from .config import ApplicationHeartbeatConfig, HeartbeatConfig, ProxyInput, ProxyType, normalize_proxy


class AsyncWebSocketClient:
    """Async WebSocket client with proxy, heartbeat, and auto-close helpers."""

    def __init__(
        self,
        url: str,
        *,
        proxy: ProxyInput = None,
        proxy_type: ProxyType = "http",
        proxy_username: str | None = None,
        proxy_password: str | None = None,
        headers: Mapping[str, str] | None = None,
        subprotocols: Sequence[str] | None = None,
        heartbeat: bool = True,
        heartbeat_interval: float | None = 20.0,
        heartbeat_timeout: float | None = 20.0,
        app_heartbeat: bool = False,
        app_heartbeat_message: Any = "ping",
        app_heartbeat_interval: float = 30.0,
        app_heartbeat_json: bool | None = None,
        app_heartbeat_hex: bool = False,
        app_heartbeat_immediate: bool = False,
        app_heartbeat_text: bool | None = None,
        open_timeout: float | None = 10.0,
        close_timeout: float | None = 10.0,
        max_size: int | None = 1024 * 1024,
        compression: str | None = "deflate",
        user_agent_header: str | None = None,
        **connect_options: Any,
    ) -> None:
        self.url = url
        self.headers = dict(headers or {})
        self.subprotocols = list(subprotocols) if subprotocols else None
        self.heartbeat = HeartbeatConfig(
            enabled=heartbeat and heartbeat_interval is not None,
            interval=heartbeat_interval,
            timeout=heartbeat_timeout,
        )
        self.app_heartbeat = ApplicationHeartbeatConfig(
            enabled=app_heartbeat,
            message=app_heartbeat_message,
            interval=app_heartbeat_interval,
            as_json=app_heartbeat_json,
            as_hex=app_heartbeat_hex,
            immediate=app_heartbeat_immediate,
            text=app_heartbeat_text,
        )
        self.open_timeout = open_timeout
        self.close_timeout = close_timeout
        self.max_size = max_size
        self.compression = compression
        self.user_agent_header = user_agent_header
        self.connect_options = dict(connect_options)
        self._proxy_url = normalize_proxy(
            proxy,
            proxy_type=proxy_type,
            proxy_username=proxy_username,
            proxy_password=proxy_password,
        )
        self._conn: Any | None = None
        self._app_heartbeat_task: asyncio.Task[None] | None = None
        self._send_lock = asyncio.Lock()

    @classmethod
    async def create(cls, url: str, **kwargs: Any) -> "AsyncWebSocketClient":
        client = cls(url, **kwargs)
        await client.connect()
        return client

    @property
    def proxy_url(self) -> str | bool | None:
        return self._proxy_url

    @property
    def connected(self) -> bool:
        return self._conn is not None

    @property
    def raw_connection(self) -> Any:
        return self._require_connection()

    async def connect(self) -> "AsyncWebSocketClient":
        if self._conn is not None:
            return self

        self._conn = await async_connect(self.url, **self._build_connect_kwargs())
        self._start_app_heartbeat()
        return self

    async def close(self, code: int = 1000, reason: str = "") -> None:
        await self._stop_app_heartbeat()
        conn = self._conn
        self._conn = None
        if conn is not None:
            await conn.close(code=code, reason=reason)

    async def reconnect(self) -> "AsyncWebSocketClient":
        await self.close()
        return await self.connect()

    async def send(
        self,
        message: str | bytes | bytearray | memoryview,
        *,
        text: bool | None = None,
    ) -> None:
        async with self._send_lock:
            await self._require_connection().send(message, text=text)

    async def send_text(self, text: str) -> None:
        await self.send(text)

    async def send_bytes(self, data: bytes | bytearray | memoryview) -> None:
        await self.send(data)

    async def send_hex(self, data: str | bytes | bytearray | memoryview) -> None:
        await self.send_bytes(bytes_from_hex(data))

    async def send_json(self, data: Any, **json_kwargs: Any) -> None:
        payload = json.dumps(
            data,
            ensure_ascii=json_kwargs.pop("ensure_ascii", False),
            separators=json_kwargs.pop("separators", (",", ":")),
            **json_kwargs,
        )
        await self.send_text(payload)

    async def recv(
        self,
        *,
        timeout: float | None = None,
        decode: bool | None = None,
    ) -> str | bytes:
        coro = self._require_connection().recv(decode=decode)
        if timeout is None:
            return await coro
        return await asyncio.wait_for(coro, timeout=timeout)

    async def recv_json(
        self,
        *,
        timeout: float | None = None,
        decode: bool | None = None,
    ) -> Any:
        message = await self.recv(timeout=timeout, decode=decode)
        if isinstance(message, bytes):
            message = message.decode("utf-8")
        return json.loads(message)

    async def recv_hex(
        self,
        *,
        timeout: float | None = None,
        decode: bool | None = None,
        separator: str = "",
        uppercase: bool = False,
    ) -> str:
        return bytes_to_hex(
            await self.recv(timeout=timeout, decode=decode),
            separator=separator,
            uppercase=uppercase,
        )

    async def request(
        self,
        message: str | bytes | bytearray | memoryview,
        *,
        timeout: float | None = None,
        text: bool | None = None,
        decode: bool | None = None,
    ) -> str | bytes:
        await self.send(message, text=text)
        return await self.recv(timeout=timeout, decode=decode)

    async def request_json(self, data: Any, *, timeout: float | None = None, **json_kwargs: Any) -> Any:
        await self.send_json(data, **json_kwargs)
        return await self.recv_json(timeout=timeout)

    async def request_hex(
        self,
        data: str | bytes | bytearray | memoryview,
        *,
        timeout: float | None = None,
        separator: str = "",
        uppercase: bool = False,
    ) -> str:
        await self.send_hex(data)
        return await self.recv_hex(timeout=timeout, separator=separator, uppercase=uppercase)

    async def ping(self, data: bytes | str | None = None) -> Any:
        return await self._require_connection().ping(data)

    async def pong(self, data: bytes | str | None = None) -> None:
        await self._require_connection().pong(data)

    async def iter_messages(self) -> AsyncIterator[str | bytes]:
        async for message in self._require_connection():
            yield message

    def __aiter__(self) -> AsyncIterator[str | bytes]:
        return self.iter_messages()

    async def __aenter__(self) -> "AsyncWebSocketClient":
        return await self.connect()

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        await self.close()

    def _build_connect_kwargs(self) -> dict[str, Any]:
        kwargs = dict(self.connect_options)
        kwargs.update(
            {
                "proxy": self._proxy_url,
                "ping_interval": self.heartbeat.ping_interval,
                "ping_timeout": self.heartbeat.ping_timeout,
                "open_timeout": self.open_timeout,
                "close_timeout": self.close_timeout,
                "max_size": self.max_size,
                "compression": self.compression,
            }
        )
        if self.headers:
            kwargs["additional_headers"] = self.headers
        if self.subprotocols:
            kwargs["subprotocols"] = self.subprotocols
        if self.user_agent_header is not None:
            kwargs["user_agent_header"] = self.user_agent_header
        return kwargs

    def _require_connection(self) -> Any:
        if self._conn is None:
            raise WebSocketNotConnectedError("WebSocket is not connected; call connect() first")
        return self._conn

    def _start_app_heartbeat(self) -> None:
        if not self.app_heartbeat.enabled or self._app_heartbeat_task is not None:
            return

        self._app_heartbeat_task = asyncio.create_task(
            self._run_app_heartbeat(),
            name="easy-websocket-app-heartbeat",
        )

    async def _stop_app_heartbeat(self) -> None:
        task = self._app_heartbeat_task
        if task is None:
            return

        self._app_heartbeat_task = None
        task.cancel()
        if task is not asyncio.current_task():
            with suppress(asyncio.CancelledError):
                await task

    async def _run_app_heartbeat(self) -> None:
        try:
            if self.app_heartbeat.immediate:
                if not await self._send_app_heartbeat_once():
                    return

            while True:
                await asyncio.sleep(self.app_heartbeat.interval)
                if not await self._send_app_heartbeat_once():
                    return
        finally:
            if asyncio.current_task() is self._app_heartbeat_task:
                self._app_heartbeat_task = None

    async def _send_app_heartbeat_once(self) -> bool:
        try:
            message = self.app_heartbeat.message
            if self.app_heartbeat.as_hex:
                await self.send_hex(message)
            elif self._app_heartbeat_as_json():
                await self.send_json(message)
            else:
                await self.send(message, text=self.app_heartbeat.text)
            return True
        except Exception:
            return False

    def _app_heartbeat_as_json(self) -> bool:
        if self.app_heartbeat.as_json is not None:
            return self.app_heartbeat.as_json
        return isinstance(self.app_heartbeat.message, (dict, list, tuple))
