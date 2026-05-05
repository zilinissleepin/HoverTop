from __future__ import annotations

from pydantic import BaseModel


class DisplayItem(BaseModel):
    """单个数据展示项"""
    label: str
    value: str
    color: str | None = None


class DisplayData(BaseModel):
    """悬浮窗展示数据"""
    title: str | None = None
    subtitle: str | None = None
    items: list[DisplayItem] = []
    footer: str | None = None
