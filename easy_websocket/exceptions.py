class EasyWebSocketError(Exception):
    """Base exception for this package."""


class MissingDependencyError(ImportError):
    """Raised when the underlying WebSocket dependency isn't installed."""


class WebSocketNotConnectedError(EasyWebSocketError):
    """Raised when an operation needs an active WebSocket connection."""
