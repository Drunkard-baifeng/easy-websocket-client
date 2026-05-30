from __future__ import annotations


def bytes_from_hex(value: str | bytes | bytearray | memoryview) -> bytes:
    """Convert common hex text formats into bytes."""

    if isinstance(value, bytes):
        return value
    if isinstance(value, (bytearray, memoryview)):
        return bytes(value)
    if not isinstance(value, str):
        raise TypeError("hex value must be str or bytes-like")

    normalized = (
        value.strip()
        .replace("0x", "")
        .replace("0X", "")
        .replace(" ", "")
        .replace("\n", "")
        .replace("\r", "")
        .replace("\t", "")
        .replace("-", "")
        .replace(":", "")
    )
    if not normalized:
        return b""
    if len(normalized) % 2:
        raise ValueError("hex value must contain an even number of digits")

    try:
        return bytes.fromhex(normalized)
    except ValueError as exc:
        raise ValueError("hex value contains non-hex characters") from exc


def bytes_to_hex(
    value: str | bytes | bytearray | memoryview,
    *,
    separator: str = "",
    uppercase: bool = False,
    encoding: str = "utf-8",
) -> str:
    """Convert bytes or text into a hex string."""

    if isinstance(value, str):
        data = value.encode(encoding)
    elif isinstance(value, bytes):
        data = value
    elif isinstance(value, (bytearray, memoryview)):
        data = bytes(value)
    else:
        raise TypeError("value must be str or bytes-like")

    result = data.hex(separator) if separator else data.hex()
    return result.upper() if uppercase else result
