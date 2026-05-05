import asyncio

import pytest
import websockets

from hovertop.widget import Widget


@pytest.fixture
def widget():
    # 不自动启动 Swift app
    w = Widget(name="test", port=0, auto_launch=False)
    yield w
    w.close()


async def test_widget_start_creates_server(widget: Widget):
    widget.start()
    assert widget.port > 0
    assert widget.is_running


async def test_widget_update_sends_data(widget: Widget):
    widget.start()
    async with websockets.connect(f"ws://localhost:{widget.port}", proxy=None) as ws:
        widget.update(title="Hello", items=[{"label": "A", "value": "1"}])
        msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
        assert "Hello" in msg


async def test_widget_context_manager():
    async with Widget(name="ctx", port=0, auto_launch=False) as w:
        assert w.is_running
    # 退出后服务器应已关闭


async def test_widget_close(widget: Widget):
    widget.start()
    assert widget.is_running
    widget.close()
    assert not widget.is_running
