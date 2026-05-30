"""Convenient sync and async WebSocket clients."""

from .async_client import AsyncWebSocketClient
from .codec import bytes_from_hex, bytes_to_hex
from .config import ApplicationHeartbeatConfig, HeartbeatConfig, ProxyConfig, normalize_proxy
from .exceptions import (
    EasyWebSocketError,
    MissingDependencyError,
    WebSocketNotConnectedError,
)
from .sync_client import SyncWebSocketClient

__all__ = [
    "AsyncWebSocketClient",
    "ApplicationHeartbeatConfig",
    "bytes_from_hex",
    "bytes_to_hex",
    "EasyWebSocketError",
    "HeartbeatConfig",
    "MissingDependencyError",
    "ProxyConfig",
    "SyncWebSocketClient",
    "WebSocketNotConnectedError",
    "normalize_proxy",
]
