from __future__ import annotations

import argparse

from easy_websocket import SyncWebSocketClient


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("message")
    parser.add_argument("--proxy")
    parser.add_argument("--proxy-type", default="http")
    args = parser.parse_args()

    with SyncWebSocketClient(args.url, proxy=args.proxy, proxy_type=args.proxy_type) as ws:
        print(ws.request(args.message, timeout=10))


if __name__ == "__main__":
    main()
