from hovertop.models import DisplayData, DisplayItem


def test_display_item_minimal():
    item = DisplayItem(label="CPU", value="23%")
    assert item.label == "CPU"
    assert item.value == "23%"
    assert item.color is None


def test_display_item_with_color():
    item = DisplayItem(label="CPU", value="23%", color="#4CAF50")
    assert item.color == "#4CAF50"


def test_display_data_defaults():
    data = DisplayData()
    assert data.title is None
    assert data.subtitle is None
    assert data.items == []
    assert data.footer is None


def test_display_data_full():
    data = DisplayData(
        title="系统状态",
        subtitle="实时",
        items=[
            DisplayItem(label="CPU", value="23%", color="#4CAF50"),
            DisplayItem(label="内存", value="6GB"),
        ],
        footer="每5秒刷新",
    )
    assert len(data.items) == 2
    assert data.items[0].color == "#4CAF50"
    assert data.items[1].color is None


def test_display_data_to_dict():
    data = DisplayData(
        title="Test",
        items=[DisplayItem(label="A", value="1", color="#fff")],
    )
    d = data.model_dump()
    assert d["title"] == "Test"
    assert d["items"][0]["color"] == "#fff"
