from __future__ import annotations

from typing import Any

from hovertop.models import DisplayData, DisplayItem
from hovertop.server import WidgetServer


# 进程内已启动的悬浮窗个数, 用于让多个 Widget 在屏幕上自动错开位置
_WIDGET_COUNT = 0

# 单个窗口大致垂直占用 (px), 用于错开多个悬浮窗
_WINDOW_VSPACING = 240


class Widget:
    """悬浮窗控件的公开 API"""

    def __init__(
        self,
        name: str = "HoverTop",
        port: int = 0,
        auto_launch: bool = True,
        offset_y: float | None = None,
    ) -> None:
        """创建一个悬浮窗

        - port: WebSocket 端口, 默认 0 让 OS 自动分配 (支持同机多个悬浮窗)
        - offset_y: 窗口相对屏幕右上角默认位置向下偏移的像素;
          默认按进程内启动顺序自动递增 (0, 240, 480, ...)
        """
        self.name = name
        self._server = WidgetServer(port=port)
        self._auto_launch = auto_launch
        self._offset_y = offset_y
        self._app_process: Any = None

    @property
    def port(self) -> int:
        return self._server.port

    @property
    def is_running(self) -> bool:
        return self._server.port > 0 and self._server._server is not None

    def start(self) -> None:
        """启动 WebSocket 服务器（和可选的 Swift app）"""
        global _WIDGET_COUNT
        self._server.start()
        if self._auto_launch:
            from hovertop.app_manager import launch_app
            offset_y = self._offset_y if self._offset_y is not None else _WIDGET_COUNT * _WINDOW_VSPACING
            self._app_process = launch_app(port=self.port, offset_y=offset_y)
            _WIDGET_COUNT += 1

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
