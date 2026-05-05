from __future__ import annotations

from typing import Any

from hovertop.models import DisplayData, DisplayItem
from hovertop.server import WidgetServer


class Widget:
    """悬浮窗控件的公开 API"""

    def __init__(
        self,
        name: str = "HoverTop",
        port: int = 9527,
        auto_launch: bool = True,
    ) -> None:
        self.name = name
        self._server = WidgetServer(port=port)
        self._auto_launch = auto_launch
        self._app_process: Any = None

    @property
    def port(self) -> int:
        return self._server.port

    @property
    def is_running(self) -> bool:
        return self._server.port > 0 and self._server._server is not None

    def start(self) -> None:
        """启动 WebSocket 服务器（和可选的 Swift app）"""
        self._server.start()
        if self._auto_launch:
            from hovertop.app_manager import launch_app
            self._app_process = launch_app(port=self.port)

    def update(self, **kwargs: Any) -> None:
        """更新悬浮窗内容"""
        if not self.is_running:
            self.start()
        # 将 items 中的 dict 转换为 DisplayItem
        items_raw = kwargs.get("items", [])
        items = [
            DisplayItem(**item) if isinstance(item, dict) else item
            for item in items_raw
        ]
        kwargs["items"] = items
        data = DisplayData(**kwargs)
        self._server.send(data)

    def close(self) -> None:
        """关闭悬浮窗和服务器"""
        self._server.stop()
        if self._app_process:
            self._app_process.terminate()
            self._app_process = None

    def __enter__(self) -> Widget:
        self.start()
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    async def __aenter__(self) -> Widget:
        self.start()
        return self

    async def __aexit__(self, *args: Any) -> None:
        self.close()
