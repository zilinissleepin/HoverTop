"""股票行情悬浮窗 - A股/港股/美股 当前价和涨跌幅, 每 10 秒刷新。"""
from __future__ import annotations

import os
import sys
import time
import traceback
from typing import TypedDict

import requests


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


SINA_URL = "https://hq.sinajs.cn/list="
SINA_HEADERS = {
    "Referer": "https://finance.sina.com.cn",
    "User-Agent": "Mozilla/5.0",
}


def log_err(where: str, exc: BaseException) -> None:
    print(
        f"[{time.strftime('%H:%M:%S')}] {where}: {type(exc).__name__}: {exc}",
        file=sys.stderr,
    )
    if os.environ.get("DEBUG"):
        traceback.print_exc(file=sys.stderr)


_PARSERS = {
    "cn": parse_cn_line,
    "hk": parse_hk_line,
    "us": parse_us_line,
}


def fetch_quotes(codes: list[str], market: str) -> dict[str, Quote]:
    """批量拉取一个市场的行情, 返回 {code: Quote}, 解析失败的 code 不在 dict 中。"""
    if not codes:
        return {}
    parser = _PARSERS[market]
    url = SINA_URL + ",".join(codes)
    try:
        resp = requests.get(url, headers=SINA_HEADERS, timeout=10)
        resp.raise_for_status()
        text = resp.content.decode("gbk", errors="replace")
    except Exception as e:
        log_err(f"fetch_quotes({market})", e)
        return {}

    result: dict[str, Quote] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # 形如 var hq_str_sh600519="..."; 提取 code
        head = line.split("=", 1)[0]  # 'var hq_str_sh600519'
        parts = head.rsplit("_", 1)
        if len(parts) != 2:
            continue
        code = parts[1]
        if code not in codes:
            continue
        q = parser(code, line)
        if q is not None:
            result[code] = q
    return result


def format_price(value: float) -> str:
    """格式化股票价格。大于等于 1 的数字用千位分隔符和两位小数，小于 1 的用 4 位有效数字，0 返回 '0'。"""
    if value == 0:
        return "0"
    if abs(value) >= 1:
        return f"{value:,.2f}"
    return f"{value:.4g}"


def format_change_pct(pct: float) -> str:
    """格式化涨跌幅百分比，带正负号和两位小数。"""
    return f"{pct:+.2f}%"


COLOR_UP = "#4CAF50"
COLOR_DOWN = "#F44336"
COLOR_MISSING = "#FFFFFF"
COLOR_HEADER = "#FF9800"
DASH = "—"


def _color_for_change(pct: float) -> str:
    return COLOR_UP if pct >= 0 else COLOR_DOWN


def build_market_rows(codes: list[str], quotes: dict[str, Quote]) -> list[dict]:
    """返回 DisplayItem 等价 dict 列表, 按 change_pct 降序; 缺失的 code 排最后。"""
    rows_ok: list[tuple[float, dict]] = []
    rows_missing: list[dict] = []
    for code in codes:
        q = quotes.get(code)
        if q is None:
            rows_missing.append({
                "label": code,
                "value": "",
                "color": COLOR_MISSING,
                "cells": [DASH, DASH],
            })
            continue
        rows_ok.append((
            q["change_pct"],
            {
                "label": q["name"],
                "value": "",
                "color": _color_for_change(q["change_pct"]),
                "cells": [format_price(q["price"]), format_change_pct(q["change_pct"])],
            },
        ))
    rows_ok.sort(key=lambda r: r[0], reverse=True)
    return [row for _, row in rows_ok] + rows_missing
