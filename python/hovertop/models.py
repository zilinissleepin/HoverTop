from __future__ import annotations

from pydantic import BaseModel


class DisplayItem(BaseModel):
    """单个数据展示项

    两种模式:
    - 简单模式: label + value (左右两列)
    - 多列模式: label + cells (label 在最左, cells 是右侧多列)
    """
    label: str
    value: str = ""
    color: str | None = None
    cells: list[str] | None = None


class DisplayData(BaseModel):
    """悬浮窗展示数据"""
    title: str | None = None
    subtitle: str | None = None
    items: list[DisplayItem] = []
    footer: str | None = None
