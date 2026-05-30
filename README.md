# easy_websocket

一个轻量 Python WebSocket 客户端封装，提供同步和异步两套 API，内置代理配置、心跳、JSON 帮助方法、上下文管理自动关闭连接。

底层使用 `websockets>=15.0`。代理通过官方 `proxy=` 参数传入；SOCKS 代理依赖 `python-socks[asyncio]`。

## 安装

```bash
pip install -e .
```

或把依赖装到当前环境：

```bash
pip install "websockets>=15.0" "python-socks[asyncio]>=2.4"
```

## 同步使用

```python
from easy_websocket import SyncWebSocketClient

with SyncWebSocketClient(
    "wss://example.com/ws",
    proxy="127.0.0.1:7890",
    proxy_type="http",
    heartbeat_interval=20,
    heartbeat_timeout=10,
    app_heartbeat=True,
    app_heartbeat_message={"type": "ping"},
    app_heartbeat_interval=30,
) as ws:
    print(ws.recv_json(timeout=5))
```

## 异步使用

```python
import asyncio
from easy_websocket import AsyncWebSocketClient

async def main():
    async with AsyncWebSocketClient(
        "wss://example.com/ws",
        proxy="127.0.0.1:1080",
    proxy_type="socks5",
    heartbeat_interval=20,
    heartbeat_timeout=10,
    app_heartbeat=True,
    app_heartbeat_message="ping",
    app_heartbeat_interval=30,
) as ws:
    await ws.send_text("hello")
    print(await ws.recv(timeout=5))

asyncio.run(main())
```

## 代理写法

```python
# HTTP 代理
proxy="127.0.0.1:7890", proxy_type="http"

# HTTPS 代理
proxy="127.0.0.1:7890", proxy_type="https"

# SOCKS5 代理
proxy="127.0.0.1:1080", proxy_type="socks5"

# 带认证
proxy="127.0.0.1:1080", proxy_type="socks5", proxy_username="user", proxy_password="pass"

# 直接传完整代理 URL
proxy="socks5://user:pass@127.0.0.1:1080"

# 使用系统或环境变量中的代理配置
proxy=True

# 禁用代理，默认就是禁用
proxy=None
```

需要让 DNS 也走 SOCKS 代理时，可以使用 `proxy_type="socks5h"`。

## 常用方法

- `connect()` / `close()`：手动连接和关闭。
- `with SyncWebSocketClient(...) as ws`：同步上下文自动关闭。
- `async with AsyncWebSocketClient(...) as ws`：异步上下文自动关闭。
- `send()` / `recv()`：发送和接收文本或二进制消息。
- `send_json()` / `recv_json()`：JSON 编码和解码。
- `send_hex()` / `recv_hex()`：十六进制字符串和二进制消息互转。
- `request()` / `request_json()`：发送后等待一次响应。
- `request_hex()`：发送十六进制数据后等待一次响应，并返回十六进制字符串。
- `iter_messages()`：持续迭代接收消息。
- `reconnect()`：关闭后重新连接。

## Hex / 二进制消息

抓包工具里看到的 hex 通常是二进制内容的展示形式，发送时应该发 bytes，也就是 WebSocket binary frame：

```python
with SyncWebSocketClient("wss://example.com/ws") as ws:
    ws.send_hex("0a ff 12 34")
    print(ws.recv_hex(timeout=5))
```

支持常见写法：

```python
ws.send_hex("0aff1234")
ws.send_hex("0a ff 12 34")
ws.send_hex("0x0a 0xff 0x12 0x34")
ws.send_hex("0a:ff:12:34")
```

异步版：

```python
async with AsyncWebSocketClient("wss://example.com/ws") as ws:
    await ws.send_hex("0a ff 12 34")
    print(await ws.recv_hex(timeout=5, separator=" "))
```

如果服务端真的要求文本内容是 `"0aff1234"`，不要用 `send_hex()`，直接用 `send_text("0aff1234")`。

## 心跳

这个包支持两种心跳。

协议层心跳使用 WebSocket ping/pong frame，由底层 `websockets` 维护：

```python
SyncWebSocketClient(
    "wss://example.com/ws",
    heartbeat=True,
    heartbeat_interval=20,
    heartbeat_timeout=10,
)
```

应用层心跳会后台定时发送业务消息。同步客户端使用后台线程，异步客户端使用 `asyncio.Task`；关闭连接时会自动停止。

```python
SyncWebSocketClient(
    "wss://example.com/ws",
    app_heartbeat=True,
    app_heartbeat_message="ping",
    app_heartbeat_interval=30,
    app_heartbeat_immediate=True,
)
```

如果心跳消息是 `dict`、`list` 或 `tuple`，默认会按 JSON 发送：

```python
AsyncWebSocketClient(
    "wss://example.com/ws",
    app_heartbeat=True,
    app_heartbeat_message={"type": "ping"},
    app_heartbeat_interval=30,
)
```

也可以显式控制：

```python
app_heartbeat_json=True
app_heartbeat_text=True
```

应用层心跳也可以发送 hex 二进制：

```python
SyncWebSocketClient(
    "wss://example.com/ws",
    app_heartbeat=True,
    app_heartbeat_message="0a ff 12 34",
    app_heartbeat_hex=True,
    app_heartbeat_interval=30,
)
```

设置 `heartbeat=False` 或 `heartbeat_interval=None` 可以关闭协议层心跳；设置 `app_heartbeat=False` 可以关闭应用层心跳。

## 开发环境外网代理测试

本地可复制 `tests/dev_proxy_coinall.example.py` 为 `tests/dev_proxy_coinall.py`，填入代理后单独运行：

```powershell
.\.venv\Scripts\python.exe -m unittest tests.dev_proxy_coinall -v
```

`tests/dev_proxy_*.py` 默认会被 Git 忽略，避免把代理账号密码提交到仓库。

## Git 上传和安装

初始化仓库并提交：

```powershell
git init
git add .
git commit -m "Initial easy websocket client package"
```

推到 GitHub 或其他 Git 服务：

```powershell
git branch -M main
git remote add origin https://github.com/<your-name>/<repo-name>.git
git push -u origin main
```

其他项目可以直接从 Git 安装：

```powershell
pip install "git+https://github.com/<your-name>/<repo-name>.git"
```

固定某个分支、tag 或 commit：

```powershell
pip install "git+https://github.com/<your-name>/<repo-name>.git@main"
pip install "git+https://github.com/<your-name>/<repo-name>.git@v0.1.0"
```

本机其他项目也可以用本地路径安装：

```powershell
pip install -e E:\Project\Python\test\WebSocket
```

安装后直接使用：

```python
from easy_websocket import SyncWebSocketClient, AsyncWebSocketClient
```
