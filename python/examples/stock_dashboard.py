"""股票行情悬浮窗 - A股/港股/美股 当前价和涨跌幅, 每 10 秒刷新。"""
from __future__ import annotations

from typing import TypedDict


class Quote(TypedDict):
    name: str
    price: float
    change_pct: float


def _extract_payload(line: str) -> str | None:
    """从 'var hq_str_xxx="...";' 中取出引号内的负载, 空返回 None。"""
    if '="' not in line:
        return None
    payload = line.split('="', 1)[1].rstrip().rstrip(";").rstrip('"')
    return payload if payload else None


def parse_cn_line(code: str, line: str) -> Quote | None:
    """解析一行 A股 新浪响应。code 用于日志/容错, 当前未用。"""
    payload = _extract_payload(line)
    if not payload:
        return None
    fields = payload.split(",")
    if len(fields) < 4:
        return None
    try:
        name = fields[0]
        prev_close = float(fields[2])
        price = float(fields[3])
    except (ValueError, IndexError):
        return None
    if prev_close <= 0:
        return None
    change_pct = (price - prev_close) / prev_close * 100
    return Quote(name=name, price=price, change_pct=change_pct)


def parse_hk_line(code: str, line: str) -> Quote | None:
    """解析一行港股 新浪响应。"""
    payload = _extract_payload(line)
    if not payload:
        return None
    fields = payload.split(",")
    if len(fields) < 7:
        return None
    try:
        name = fields[1] or fields[0]  # 中文名为空时用英文名
        prev_close = float(fields[3])
        price = float(fields[6])
    except (ValueError, IndexError):
        return None
    if prev_close <= 0:
        return None
    change_pct = (price - prev_close) / prev_close * 100
    return Quote(name=name, price=price, change_pct=change_pct)


def parse_us_line(code: str, line: str) -> Quote | None:
    """解析一行美股 新浪响应。涨跌幅字段直接可用。"""
    payload = _extract_payload(line)
    if not payload:
        return None
    fields = payload.split(",")
    if len(fields) < 3:
        return None
    try:
        name = fields[0]
        price = float(fields[1])
        change_pct = float(fields[2])
    except (ValueError, IndexError):
        return None
    return Quote(name=name, price=price, change_pct=change_pct)
