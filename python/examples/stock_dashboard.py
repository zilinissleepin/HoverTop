"""股票行情悬浮窗 - A股/港股/美股 当前价和涨跌幅, 每 10 秒刷新。

数据源: 新浪财经 (https://hq.sinajs.cn), 需要带 Referer。

环境变量 (任一可空; 空的市场段不显示):
  CN_STOCKS=sh600519,sz000001      A股, 用 sh/sz 前缀
  HK_STOCKS=00700,09988            港股, 5 位代码
  US_STOCKS=AAPL,TSLA              美股, 大写 ticker
  REFRESH_INTERVAL=10              刷新间隔秒数, 默认 10

.env 放在 python/.env, 自动加载。

调用方式: uv run python examples/stock_dashboard.py
"""
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
    # 按 code 在响应中查找对应行 (不能用 rsplit("_", 1)，因为美股 code 含下划线)
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        head = line.split("=", 1)[0]  # 'var hq_str_<code>'
        prefix = "var hq_str_"
        if not head.startswith(prefix):
            continue
        code = head[len(prefix):]
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


def build_data(
    cn_codes: list[str],
    hk_codes: list[str],
    us_codes: list[str],
    refresh_interval: int,
) -> dict:
    """组装三市场数据，返回展示用的字典。"""
    sections: list[tuple[str, list[str], str]] = [
        ("A股", cn_codes, "cn"),
        ("港股", hk_codes, "hk"),
        ("美股", us_codes, "us"),
    ]
    items: list[dict] = []
    for name, codes, market in sections:
        if not codes:
            continue
        quotes = fetch_quotes(codes, market=market)
        # 分段表头
        items.append({
            "label": name,
            "value": "",
            "color": COLOR_HEADER,
            "cells": ["", ""],
        })
        items.extend(build_market_rows(codes, quotes))

    return {
        "title": "股票行情",
        "subtitle": time.strftime("%H:%M:%S"),
        "items": items,
        "footer": f"每 {refresh_interval} 秒刷新 | Ctrl+C 退出",
    }


from dotenv import load_dotenv
from hovertop import Widget


load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


def _parse_list(env_name: str) -> list[str]:
    raw = os.environ.get(env_name, "")
    return [s.strip() for s in raw.split(",") if s.strip()]


def _normalize_cn(codes: list[str]) -> list[str]:
    # 期望用户已经带 sh/sz 前缀, 小写化以匹配新浪
    return [c.lower() for c in codes]


def _normalize_hk(codes: list[str]) -> list[str]:
    # 补足到 5 位, 加 hk 前缀
    out = []
    for c in codes:
        digits = c.lower().removeprefix("hk")
        out.append("hk" + digits.zfill(5))
    return out


def _normalize_us(codes: list[str]) -> list[str]:
    # 加 gb_ 前缀并小写
    return [f"gb_{c.lower()}" for c in codes]


def main() -> None:
    cn_codes = _normalize_cn(_parse_list("CN_STOCKS"))
    hk_codes = _normalize_hk(_parse_list("HK_STOCKS"))
    us_codes = _normalize_us(_parse_list("US_STOCKS"))
    refresh_interval = int(os.environ.get("REFRESH_INTERVAL", "10"))

    if not (cn_codes or hk_codes or us_codes):
        print("未配置任何股票. 请在 .env 中设置 CN_STOCKS / HK_STOCKS / US_STOCKS.", file=sys.stderr)
        sys.exit(1)

    with Widget("股票行情") as widget:
        print("股票行情悬浮窗已启动, 按 Ctrl+C 退出...")
        while True:
            try:
                data = build_data(cn_codes, hk_codes, us_codes, refresh_interval)
                widget.update(**data)
            except Exception as e:
                log_err("build_data/update", e)
                widget.update(
                    title="股票行情",
                    subtitle="数据获取失败",
                    items=[{"label": "错误", "value": str(e)[:50], "color": COLOR_DOWN}],
                )
            time.sleep(refresh_interval)


if __name__ == "__main__":
    main()
