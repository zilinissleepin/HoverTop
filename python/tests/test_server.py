import asyncio
import json

import pytest
import websockets

from hovertop.models import DisplayData, DisplayItem
from hovertop.server import WidgetServer


@pytest.fixture
def server():
    s = WidgetServer(port=0)  # 随机端口
    yield s
    s.stop()


async def test_server_start_stop(server: WidgetServer):
    server.start()
    assert server.port > 0
    server.stop()


async def test_server_receives_connection(server: WidgetServer):
    server.start()
    async with websockets.connect(f"ws://localhost:{server.port}", proxy=None) as ws:
        # 连接成功，服务器应接受
        pass


async def test_server_sends_data(server: WidgetServer):
    server.start()
    data = DisplayData(
        title="Test",
        items=[DisplayItem(label="CPU", value="50%")],
    )
    async with websockets.connect(f"ws://localhost:{server.port}", proxy=None) as ws:
        server.send(data)
        msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
        parsed = json.loads(msg)
        assert parsed["title"] == "Test"
        assert parsed["items"][0]["label"] == "CPU"


async def test_server_send_without_connection(server: WidgetServer):
    server.start()
    data = DisplayData(title="No client")
    # 不应抛异常
    server.send(data)
