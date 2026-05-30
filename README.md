# easy_websocket

`easy_websocket` 是一个轻量 Python WebSocket 客户端封装，基于 `websockets`，提供同步和异步两套 API。

它适合把常见 WebSocket 使用细节收拢起来：代理、协议层心跳、应用层心跳、JSON、二进制 hex、上下文自动关闭连接。

## 功能

- 同步客户端：`SyncWebSocketClient`
- 异步客户端：`AsyncWebSocketClient`
- HTTP / HTTPS / SOCKS5 代理
- 代理认证：`username` / `password`
- WebSocket 协议层 ping/pong 心跳
- 应用层业务心跳：文本、JSON、hex 二进制
- JSON 发送和接收
- hex 字符串和 binary frame 自动互转
- `with` / `async with` 自动连接和关闭

## 安装

从 GitHub 安装：

```powershell
pip install "git+https://github.com/Drunkard-baifeng/easy-websocket-client.git"
```

指定分支、tag 或 commit：

```powershell
pip install "git+https://github.com/Drunkard-baifeng/easy-websocket-client.git@main"
pip install "git+https://github.com/Drunkard-baifeng/easy-websocket-client.git@v0.1.0"
```

写进 `requirements.txt`：

```txt
easy-websocket-client @ git+https://github.com/Drunkard-baifeng/easy-websocket-client.git@main
```

本地开发安装：

```powershell
git clone https://github.com/Drunkard-baifeng/easy-websocket-client.git
cd easy-websocket-client
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
```

## 快速开始

同步：

```python
from easy_websocket import SyncWebSocketClient

with SyncWebSocketClient("wss://example.com/ws") as ws:
    ws.send_text("hello")
    print(ws.recv(timeout=5))
```

异步：

```python
import asyncio

from easy_websocket import AsyncWebSocketClient


async def main():
    async with AsyncWebSocketClient("wss://example.com/ws") as ws:
        await ws.send_text("hello")
        print(await ws.recv(timeout=5))


asyncio.run(main())
```

## 代理

HTTP 代理：

```python
with SyncWebSocketClient(
    "wss://example.com/ws",
    proxy="127.0.0.1:7890",
    proxy_type="http",
) as ws:
    ...
```

SOCKS5 代理：

```python
with SyncWebSocketClient(
    "wss://example.com/ws",
    proxy="127.0.0.1:1080",
    proxy_type="socks5",
) as ws:
    ...
```

带账号密码：

```python
with SyncWebSocketClient(
    "wss://example.com/ws",
    proxy="127.0.0.1:1080",
    proxy_type="socks5",
    proxy_username="user",
    proxy_password="pass",
) as ws:
    ...
```

也可以直接传完整代理 URL：

```python
proxy="socks5://user:pass@127.0.0.1:1080"
```

常见取值：

```python
proxy_type="http"
proxy_type="https"
proxy_type="socks5"
proxy_type="socks5h"  # DNS 也走代理
```

禁用代理：

```python
proxy=None
```

使用系统或环境变量代理：

```python
proxy=True
```

## 请求头和 Origin

普通请求头使用 `headers`：

```python
headers = {
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
}
```

`Origin`、`ssl` 等底层 `websockets.connect()` 参数可以直接传给客户端：

```python
with SyncWebSocketClient(
    "wss://example.com/ws",
    headers=headers,
    origin="https://example.com",
    user_agent_header="Mozilla/5.0",
) as ws:
    ...
```

`Host`、`Connection`、`Upgrade`、`Sec-WebSocket-Key`、`Sec-WebSocket-Version` 这类握手头由底层库自动生成，一般不要手动传。

## JSON

```python
with SyncWebSocketClient("wss://example.com/ws") as ws:
    ws.send_json({"op": "ping"})
    data = ws.recv_json(timeout=5)
```

异步：

```python
async with AsyncWebSocketClient("wss://example.com/ws") as ws:
    await ws.send_json({"op": "ping"})
    data = await ws.recv_json(timeout=5)
```

## Hex / 二进制

抓包工具里看到的 hex 通常只是二进制内容的展示形式。发送时应该发 bytes，也就是 WebSocket binary frame。

```python
with SyncWebSocketClient("wss://example.com/ws") as ws:
    ws.send_hex("0a ff 12 34")
    print(ws.recv_hex(timeout=5))
```

支持这些写法：

```python
ws.send_hex("0aff1234")
ws.send_hex("0a ff 12 34")
ws.send_hex("0x0a 0xff 0x12 0x34")
ws.send_hex("0a:ff:12:34")
ws.send_hex("0a-ff-12-34")
```

请求并返回 hex：

```python
reply_hex = ws.request_hex("0a ff 12 34", timeout=5)
reply_hex = ws.request_hex("0a ff 12 34", timeout=5, separator=" ", uppercase=True)
```

如果服务端要求文本内容就是 `"0aff1234"`，不要用 `send_hex()`，直接用：

```python
ws.send_text("0aff1234")
```

## 心跳

有两种心跳，名字故意分开。

协议层心跳是 WebSocket ping/pong frame，由底层 `websockets` 维护：

```python
with SyncWebSocketClient(
    "wss://example.com/ws",
    heartbeat=True,
    heartbeat_interval=20,
    heartbeat_timeout=10,
) as ws:
    ...
```

应用层心跳是业务消息，客户端会后台定时发送。同步版使用后台线程，异步版使用 `asyncio.Task`；连接关闭时会自动停止。

发送文本：

```python
with SyncWebSocketClient(
    "wss://example.com/ws",
    app_heartbeat=True,
    app_heartbeat_message="ping",
    app_heartbeat_interval=30,
    app_heartbeat_immediate=True,
) as ws:
    ...
```

发送 JSON：

```python
with SyncWebSocketClient(
    "wss://example.com/ws",
    app_heartbeat=True,
    app_heartbeat_message={"op": "ping"},
    app_heartbeat_interval=30,
) as ws:
    ...
```

发送 hex 二进制：

```python
with SyncWebSocketClient(
    "wss://example.com/ws",
    app_heartbeat=True,
    app_heartbeat_message="0a ff 12 34",
    app_heartbeat_hex=True,
    app_heartbeat_interval=30,
) as ws:
    ...
```

关闭心跳：

```python
heartbeat=False
app_heartbeat=False
```

## 常用方法

```python
connect()
close()
reconnect()

send()
send_text()
send_bytes()
send_json()
send_hex()

recv()
recv_json()
recv_hex()

request()
request_json()
request_hex()

iter_messages()
```

## 开发测试

运行普通测试：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

外网代理开发测试不会进入普通测试。需要时复制模板：

```powershell
Copy-Item tests\dev_proxy_coinall.example.py tests\dev_proxy_coinall.py
```

填入代理后单独运行：

```powershell
.\.venv\Scripts\python.exe -m unittest tests.dev_proxy_coinall -v
```

`tests/dev_proxy_*.py` 已加入 `.gitignore`，避免把代理账号密码提交到仓库。

## 依赖

- Python `>=3.10`
- `websockets>=15.0`
- `python-socks[asyncio]>=2.4`

依赖会在安装本包时自动安装。
