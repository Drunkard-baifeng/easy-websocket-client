from __future__ import annotations

import json
import threading
from contextlib import suppress
from typing import Any, Iterator, Mapping, Sequence

from .codec import bytes_from_hex, bytes_to_hex
from .exceptions import MissingDependencyError, WebSocketNotConnectedError

try:
    from websockets.sync.client import connect as sync_connect
except ImportError as exc:
    raise MissingDependencyError(
        'Install dependencies with: pip install "websockets>=15.0" '
        '"python-socks[asyncio]>=2.4"'
    ) from exc

from .config import ApplicationHeartbeatConfig, HeartbeatConfig, ProxyInput, ProxyType, normalize_proxy


class SyncWebSocketClient:
    """Synchronous WebSocket client with proxy, heartbeat, and auto-close helpers."""

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
        auto_connect: bool = False,
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
        self._app_heartbeat_thread: threading.Thread | None = None
        self._app_heartbeat_stop = threading.Event()
        self._send_lock = threading.Lock()

        if auto_connect:
            self.connect()

    @property
    def proxy_url(self) -> str | bool | None:
        return self._proxy_url

    @property
    def connected(self) -> bool:
        return self._conn is not None

    @property
    def raw_connection(self) -> Any:
        return self._require_connection()

    def connect(self) -> "SyncWebSocketClient":
        if self._conn is not None:
            return self

        self._conn = sync_connect(self.url, **self._build_connect_kwargs())
        self._start_app_heartbeat()
        return self

    def close(self, code: int = 1000, reason: str = "") -> None:
        self._stop_app_heartbeat()
        conn = self._conn
        self._conn = None
        if conn is not None:
            conn.close(code=code, reason=reason)

    def reconnect(self) -> "SyncWebSocketClient":
        self.close()
        return self.connect()

    def send(self, message: str | bytes | bytearray | memoryview, *, text: bool | None = None) -> None:
        with self._send_lock:
            self._require_connection().send(message, text=text)

    def send_text(self, text: str) -> None:
        self.send(text)

    def send_bytes(self, data: bytes | bytearray | memoryview) -> None:
        self.send(data)

    def send_hex(self, data: str | bytes | bytearray | memoryview) -> None:
        self.send_bytes(bytes_from_hex(data))

    def send_json(self, data: Any, **json_kwargs: Any) -> None:
        payload = json.dumps(
            data,
            ensure_ascii=json_kwargs.pop("ensure_ascii", False),
            separators=json_kwargs.pop("separators", (",", ":")),
            **json_kwargs,
        )
        self.send_text(payload)

    def recv(self, *, timeout: float | None = None, decode: bool | None = None) -> str | bytes:
        return self._require_connection().recv(timeout=timeout, decode=decode)

    def recv_json(self, *, timeout: float | None = None, decode: bool | None = None) -> Any:
        message = self.recv(timeout=timeout, decode=decode)
        if isinstance(message, bytes):
            message = message.decode("utf-8")
        return json.loads(message)

    def recv_hex(
        self,
        *,
        timeout: float | None = None,
        decode: bool | None = None,
        separator: str = "",
        uppercase: bool = False,
    ) -> str:
        return bytes_to_hex(
            self.recv(timeout=timeout, decode=decode),
            separator=separator,
            uppercase=uppercase,
        )

    def request(
        self,
        message: str | bytes | bytearray | memoryview,
        *,
        timeout: float | None = None,
        text: bool | None = None,
        decode: bool | None = None,
    ) -> str | bytes:
        self.send(message, text=text)
        return self.recv(timeout=timeout, decode=decode)

    def request_json(self, data: Any, *, timeout: float | None = None, **json_kwargs: Any) -> Any:
        self.send_json(data, **json_kwargs)
        return self.recv_json(timeout=timeout)

    def request_hex(
        self,
        data: str | bytes | bytearray | memoryview,
        *,
        timeout: float | None = None,
        separator: str = "",
        uppercase: bool = False,
    ) -> str:
        self.send_hex(data)
        return self.recv_hex(timeout=timeout, separator=separator, uppercase=uppercase)

    def ping(self, data: bytes | str | None = None) -> Any:
        return self._require_connection().ping(data)

    def pong(self, data: bytes | str | None = None) -> None:
        self._require_connection().pong(data)

    def iter_messages(self) -> Iterator[str | bytes]:
        yield from self._require_connection()

    def __iter__(self) -> Iterator[str | bytes]:
        return self.iter_messages()

    def __enter__(self) -> "SyncWebSocketClient":
        return self.connect()

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def __del__(self) -> None:
        with suppress(Exception):
            self.close()

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
        if not self.app_heartbeat.enabled or self._app_heartbeat_thread is not None:
            return

        self._app_heartbeat_stop.clear()
        self._app_heartbeat_thread = threading.Thread(
            target=self._run_app_heartbeat,
            name="easy-websocket-app-heartbeat",
            daemon=True,
        )
        self._app_heartbeat_thread.start()

    def _stop_app_heartbeat(self) -> None:
        thread = self._app_heartbeat_thread
        if thread is None:
            return

        self._app_heartbeat_stop.set()
        if thread is not threading.current_thread():
            thread.join(timeout=min(self.app_heartbeat.interval, 1.0))
        self._app_heartbeat_thread = None

    def _run_app_heartbeat(self) -> None:
        try:
            if self.app_heartbeat.immediate:
                if not self._send_app_heartbeat_once():
                    return

            while not self._app_heartbeat_stop.wait(self.app_heartbeat.interval):
                if not self._send_app_heartbeat_once():
                    return
        finally:
            if threading.current_thread() is self._app_heartbeat_thread:
                self._app_heartbeat_thread = None

    def _send_app_heartbeat_once(self) -> bool:
        try:
            message = self.app_heartbeat.message
            if self.app_heartbeat.as_hex:
                self.send_hex(message)
            elif self._app_heartbeat_as_json():
                self.send_json(message)
            else:
                self.send(message, text=self.app_heartbeat.text)
            return True
        except Exception:
            self._app_heartbeat_stop.set()
            return False

    def _app_heartbeat_as_json(self) -> bool:
        if self.app_heartbeat.as_json is not None:
            return self.app_heartbeat.as_json
        return isinstance(self.app_heartbeat.message, (dict, list, tuple))
