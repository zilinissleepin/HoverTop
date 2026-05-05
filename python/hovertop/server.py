from __future__ import annotations

import asyncio
import json
import threading
import time
from typing import Any

import websockets
import websockets.server

from hovertop.models import DisplayData


class WidgetServer:
    """内嵌 WebSocket 服务器，供 Swift 客户端连接"""

    def __init__(self, port: int = 9527) -> None:
        self._requested_port = port
        self.port: int = 0
        self._server: websockets.server.WebSocketServer | None = None
        self._client: Any = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None

    def _run_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._serve())
        self._loop.run_forever()

    async def _serve(self) -> None:
        self._server = await websockets.serve(
            self._handler,
            "localhost",
            self._requested_port,
        )
        self.port = self._server.sockets[0].getsockname()[1]

    async def _handler(self, websocket: Any) -> None:
        self._client = websocket
        try:
            async for _ in websocket:
                pass  # 纯展示，不处理客户端消息
        finally:
            self._client = None

    def start(self) -> None:
        """在后台线程启动服务器"""
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        # 等待服务器就绪
        for _ in range(50):
            if self.port > 0:
                return
            time.sleep(0.1)
        raise RuntimeError("WebSocket server failed to start")

    def stop(self) -> None:
        """停止服务器"""
        if self._server and self._loop:
            self._loop.call_soon_threadsafe(self._shutdown)
            if self._thread:
                self._thread.join(timeout=3.0)

    def _shutdown(self) -> None:
        """在事件循环中执行优雅关闭"""
        if self._server:
            self._server.close()
            assert self._loop is not None
            self._loop.create_task(self._await_close())

    async def _await_close(self) -> None:
        """等待服务器关闭后停止事件循环"""
        if self._server:
            await self._server.wait_closed()
        if self._loop:
            self._loop.stop()

    def send(self, data: DisplayData) -> None:
        """发送数据到已连接的客户端"""
        if self._client and self._loop:
            msg = data.model_dump_json()
            asyncio.run_coroutine_threadsafe(
                self._client.send(msg), self._loop
            )
