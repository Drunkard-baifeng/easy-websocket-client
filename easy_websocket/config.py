from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping, TypeAlias
from urllib.parse import quote, urlsplit

ProxyType: TypeAlias = Literal[
    "http",
    "https",
    "socks4",
    "socks4a",
    "socks5",
    "socks5h",
]
ProxyInput: TypeAlias = "ProxyConfig | str | Mapping[str, Any] | bool | None"

SUPPORTED_PROXY_TYPES: tuple[str, ...] = (
    "http",
    "https",
    "socks4",
    "socks4a",
    "socks5",
    "socks5h",
)


@dataclass(frozen=True)
class ProxyConfig:
    """Proxy settings accepted by websockets' ``proxy=`` argument."""

    address: str
    type: ProxyType = "http"
    username: str | None = None
    password: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.address, str) or not self.address.strip():
            raise ValueError("proxy address must be a non-empty string")

        normalized_type = _normalize_proxy_type(self.type)
        object.__setattr__(self, "type", normalized_type)
        object.__setattr__(self, "address", self.address.strip())

    def to_url(self) -> str:
        raw = self.address
        parsed = urlsplit(raw)
        scheme = parsed.scheme.lower() if parsed.scheme else self.type

        if scheme not in SUPPORTED_PROXY_TYPES:
            supported = ", ".join(SUPPORTED_PROXY_TYPES)
            raise ValueError(f"unsupported proxy type {scheme!r}; use one of: {supported}")

        if parsed.scheme:
            host = parsed.hostname
            if not host:
                raise ValueError("proxy URL must include a host")
            try:
                port = parsed.port
            except ValueError as exc:
                raise ValueError("proxy URL must include a valid port") from exc
            if port is None:
                raise ValueError("proxy URL must include a port")
            username = parsed.username if parsed.username is not None else self.username
            password = parsed.password if parsed.password is not None else self.password
            hostport = _format_host_port(host, port)
        else:
            host, port = _split_host_port(raw)
            username = self.username
            password = self.password
            hostport = f"{host}:{port}"

        return f"{scheme}://{_format_auth(username, password)}{hostport}"


@dataclass(frozen=True)
class HeartbeatConfig:
    """Ping/pong keepalive settings."""

    enabled: bool = True
    interval: float | None = 20.0
    timeout: float | None = 20.0

    def __post_init__(self) -> None:
        if self.interval is not None and self.interval < 0:
            raise ValueError("heartbeat interval must be >= 0 or None")
        if self.timeout is not None and self.timeout < 0:
            raise ValueError("heartbeat timeout must be >= 0 or None")

    @property
    def ping_interval(self) -> float | None:
        return self.interval if self.enabled else None

    @property
    def ping_timeout(self) -> float | None:
        return self.timeout if self.enabled else None


@dataclass(frozen=True)
class ApplicationHeartbeatConfig:
    """Application-level heartbeat messages sent by this wrapper."""

    enabled: bool = False
    message: Any = "ping"
    interval: float = 30.0
    as_json: bool | None = None
    as_hex: bool = False
    immediate: bool = False
    text: bool | None = None

    def __post_init__(self) -> None:
        if self.interval <= 0:
            raise ValueError("application heartbeat interval must be > 0")
        if self.as_json and self.as_hex:
            raise ValueError("application heartbeat cannot be both JSON and hex")


def normalize_proxy(
    proxy: ProxyInput,
    *,
    proxy_type: ProxyType = "http",
    proxy_username: str | None = None,
    proxy_password: str | None = None,
) -> str | Literal[True] | None:
    """Normalize flexible proxy input into ``websockets.connect(proxy=...)``."""

    if proxy is None or proxy is False:
        return None
    if proxy is True:
        return True
    if isinstance(proxy, ProxyConfig):
        return proxy.to_url()
    if isinstance(proxy, str):
        return ProxyConfig(
            proxy,
            type=proxy_type,
            username=proxy_username,
            password=proxy_password,
        ).to_url()
    if isinstance(proxy, Mapping):
        return _proxy_from_mapping(
            proxy,
            default_type=proxy_type,
            default_username=proxy_username,
            default_password=proxy_password,
        ).to_url()

    raise TypeError("proxy must be None, True, str, mapping, or ProxyConfig")


def _proxy_from_mapping(
    proxy: Mapping[str, Any],
    *,
    default_type: ProxyType,
    default_username: str | None,
    default_password: str | None,
) -> ProxyConfig:
    address = proxy.get("address") or proxy.get("addr") or proxy.get("proxy")
    if not address:
        host = proxy.get("host") or proxy.get("ip")
        port = proxy.get("port")
        if host and port:
            address = f"{host}:{port}"

    if not address:
        raise ValueError("proxy mapping must contain address/proxy or host/ip plus port")

    return ProxyConfig(
        str(address),
        type=proxy.get("type") or proxy.get("proxy_type") or default_type,
        username=proxy.get("username") or proxy.get("user") or default_username,
        password=proxy.get("password") or proxy.get("pass") or default_password,
    )


def _normalize_proxy_type(proxy_type: str) -> ProxyType:
    value = str(proxy_type).strip().lower()
    if value not in SUPPORTED_PROXY_TYPES:
        supported = ", ".join(SUPPORTED_PROXY_TYPES)
        raise ValueError(f"unsupported proxy type {value!r}; use one of: {supported}")
    return value  # type: ignore[return-value]


def _split_host_port(address: str) -> tuple[str, str]:
    if address.startswith("["):
        end = address.find("]")
        if end == -1 or len(address) <= end + 2 or address[end + 1] != ":":
            raise ValueError("proxy address must be in host:port format")
        host = address[: end + 1]
        port = address[end + 2 :]
    else:
        host, sep, port = address.rpartition(":")
        if not sep:
            raise ValueError("proxy address must be in host:port format")

    if not host or not port:
        raise ValueError("proxy address must be in host:port format")
    if not port.isdigit():
        raise ValueError("proxy port must be a number")

    return host, port


def _format_host_port(host: str, port: int) -> str:
    if ":" in host and not (host.startswith("[") and host.endswith("]")):
        host = f"[{host}]"
    return f"{host}:{port}"


def _format_auth(username: str | None, password: str | None) -> str:
    if username is None:
        return ""
    safe_username = quote(username, safe="")
    if password is None:
        return f"{safe_username}@"
    return f"{safe_username}:{quote(password, safe='')}@"
