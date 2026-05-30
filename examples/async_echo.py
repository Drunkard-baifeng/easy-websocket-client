from __future__ import annotations

import argparse
import asyncio

from easy_websocket import AsyncWebSocketClient


async def amain() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("message")
    parser.add_argument("--proxy")
    parser.add_argument("--proxy-type", default="http")
    args = parser.parse_args()

    async with AsyncWebSocketClient(args.url, proxy=args.proxy, proxy_type=args.proxy_type) as ws:
        print(await ws.request(args.message, timeout=10))


if __name__ == "__main__":
    asyncio.run(amain())
