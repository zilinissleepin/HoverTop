# 股票行情悬浮窗 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增 `examples/stock_dashboard.py`，用新浪财经 API 实时展示 A股/港股/美股 行情（当前价 + 涨跌幅），每 10 秒刷新。

**Architecture:** 单文件脚本，内部拆成 `parse_*` 纯函数（负责解析新浪响应文本）、`fetch_*` 函数（HTTP + parse）、`build_data()` 组装悬浮窗数据、`main()` 循环。解析函数是纯函数，便于 TDD。

**Tech Stack:** Python 3.10+、`requests`、`python-dotenv`、`pydantic`（已有）、`pytest`（已有）。无新增依赖。

**Spec:** `docs/superpowers/specs/2026-05-08-stock-dashboard-design.md`

---

## 文件结构

- 创建 `python/examples/stock_dashboard.py` — 单文件脚本，含所有函数 + `main()`
- 创建 `python/tests/test_stock_dashboard.py` — 解析函数和排序逻辑的单测
- 创建 `python/tests/conftest.py` — 把 `examples/` 加入 `sys.path`，方便测试导入

---

### Task 1: 允许测试从 `examples/` 导入

**Files:**
- Create: `python/tests/conftest.py`

- [ ] **Step 1: 创建 conftest.py**

```python
"""把 examples/ 加入 sys.path, 让 test_stock_dashboard 可以 import examples 里的模块。"""
import sys
from pathlib import Path

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))
```

- [ ] **Step 2: 创建占位 examples/stock_dashboard.py 让 import 不报错**

文件内容暂时只放一行：

```python
"""股票行情悬浮窗 - A股/港股/美股 当前价和涨跌幅, 每 10 秒刷新。"""
```

- [ ] **Step 3: 验证 pytest 能收集到 tests 目录**

Run: `cd python && uv run pytest --collect-only -q`
Expected: 列出已有测试（test_widget 等），无 ImportError。

- [ ] **Step 4: Commit**

```bash
git add python/tests/conftest.py python/examples/stock_dashboard.py
git commit -m "test: 添加 conftest 让 tests 能导入 examples 模块"
```

---

### Task 2: 解析 A股 响应（`parse_cn_line`）

**背景**：新浪 A股 响应每行格式：
`var hq_str_sh600519="贵州茅台,1630.00,1630.00,1650.00,1660.00,1620.00,...";`
字段顺序：`[0]名称 [1]今开 [2]昨收 [3]当前价 [4]最高 [5]最低 ...`
涨跌幅自算：`(current - prev_close) / prev_close * 100`

**Files:**
- Modify: `python/examples/stock_dashboard.py` — 新增 `Quote` 和 `parse_cn_line`
- Test: `python/tests/test_stock_dashboard.py`

- [ ] **Step 1: 写失败测试**

创建 `python/tests/test_stock_dashboard.py`：

```python
"""stock_dashboard 解析与排序的单元测试。"""
from __future__ import annotations

import pytest

from stock_dashboard import Quote, parse_cn_line


def test_parse_cn_line_normal():
    line = 'var hq_str_sh600519="贵州茅台,1630.00,1630.00,1650.00,1660.00,1620.00,extra,fields";'
    q = parse_cn_line("sh600519", line)
    assert q is not None
    assert q["name"] == "贵州茅台"
    assert q["price"] == pytest.approx(1650.00)
    # 涨跌幅 = (1650 - 1630) / 1630 * 100 ≈ 1.2270
    assert q["change_pct"] == pytest.approx((1650.00 - 1630.00) / 1630.00 * 100)


def test_parse_cn_line_empty_payload():
    # 无效代码时新浪返回 var hq_str_xxx="";
    line = 'var hq_str_sh999999="";'
    assert parse_cn_line("sh999999", line) is None


def test_parse_cn_line_zero_prev_close():
    # 昨收为 0 时避免除零
    line = 'var hq_str_sh000000="测试,0.00,0.00,0.00,0.00,0.00,a,b";'
    q = parse_cn_line("sh000000", line)
    assert q is None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd python && uv run pytest tests/test_stock_dashboard.py -v`
Expected: `ImportError: cannot import name 'Quote'` 或 `parse_cn_line`。

- [ ] **Step 3: 写最小实现**

编辑 `python/examples/stock_dashboard.py`：

```python
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd python && uv run pytest tests/test_stock_dashboard.py -v`
Expected: 3 passed。

- [ ] **Step 5: Commit**

```bash
git add python/examples/stock_dashboard.py python/tests/test_stock_dashboard.py
git commit -m "feat: A股行情响应解析 parse_cn_line"
```

---

### Task 3: 解析 港股 响应（`parse_hk_line`）

**背景**：港股字段顺序：`[0]英文名 [1]中文名 [2]今开 [3]昨收 [4]最高 [5]最低 [6]当前价 ...`
涨跌幅自算，名称取中文名（`fields[1]`），若为空回退到英文名（`fields[0]`）。

**Files:**
- Modify: `python/examples/stock_dashboard.py`
- Test: `python/tests/test_stock_dashboard.py`

- [ ] **Step 1: 写失败测试**

在 `test_stock_dashboard.py` 末尾追加：

```python
from stock_dashboard import parse_hk_line


def test_parse_hk_line_normal():
    # fields: 英文名, 中文名, 今开, 昨收, 最高, 最低, 当前价, ...
    line = 'var hq_str_hk00700="TENCENT,腾讯控股,378.00,380.00,382.00,376.00,381.00,extra";'
    q = parse_hk_line("hk00700", line)
    assert q is not None
    assert q["name"] == "腾讯控股"
    assert q["price"] == pytest.approx(381.00)
    assert q["change_pct"] == pytest.approx((381.00 - 380.00) / 380.00 * 100)


def test_parse_hk_line_fallback_to_english_name():
    line = 'var hq_str_hk00700="TENCENT,,378.00,380.00,382.00,376.00,381.00,extra";'
    q = parse_hk_line("hk00700", line)
    assert q is not None
    assert q["name"] == "TENCENT"


def test_parse_hk_line_empty_payload():
    line = 'var hq_str_hk99999="";'
    assert parse_hk_line("hk99999", line) is None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd python && uv run pytest tests/test_stock_dashboard.py::test_parse_hk_line_normal -v`
Expected: ImportError。

- [ ] **Step 3: 实现**

追加到 `stock_dashboard.py`：

```python
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd python && uv run pytest tests/test_stock_dashboard.py -v`
Expected: 6 passed。

- [ ] **Step 5: Commit**

```bash
git add python/examples/stock_dashboard.py python/tests/test_stock_dashboard.py
git commit -m "feat: 港股行情响应解析 parse_hk_line"
```

---

### Task 4: 解析 美股 响应（`parse_us_line`）

**背景**：美股字段顺序较长，关键字段：`[0]名称 [1]当前价 [2]涨跌幅 [3]日期 ...`
涨跌幅字段直接可用，无需自算。

**Files:**
- Modify: `python/examples/stock_dashboard.py`
- Test: `python/tests/test_stock_dashboard.py`

- [ ] **Step 1: 写失败测试**

追加：

```python
from stock_dashboard import parse_us_line


def test_parse_us_line_normal():
    # [0]名称 [1]当前价 [2]涨跌幅 [3]日期, 后面字段省略
    line = 'var hq_str_gb_aapl="Apple Inc,175.50,0.8614,2026-05-08 09:30:00,...";'
    q = parse_us_line("gb_aapl", line)
    assert q is not None
    assert q["name"] == "Apple Inc"
    assert q["price"] == pytest.approx(175.50)
    assert q["change_pct"] == pytest.approx(0.8614)


def test_parse_us_line_negative_change():
    line = 'var hq_str_gb_tsla="Tesla Inc,245.00,-2.30,2026-05-08 09:30:00,...";'
    q = parse_us_line("gb_tsla", line)
    assert q is not None
    assert q["change_pct"] == pytest.approx(-2.30)


def test_parse_us_line_empty_payload():
    line = 'var hq_str_gb_xxxx="";'
    assert parse_us_line("gb_xxxx", line) is None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd python && uv run pytest tests/test_stock_dashboard.py::test_parse_us_line_normal -v`
Expected: ImportError。

- [ ] **Step 3: 实现**

追加：

```python
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd python && uv run pytest tests/test_stock_dashboard.py -v`
Expected: 9 passed。

- [ ] **Step 5: Commit**

```bash
git add python/examples/stock_dashboard.py python/tests/test_stock_dashboard.py
git commit -m "feat: 美股行情响应解析 parse_us_line"
```

---

### Task 5: 批量行情获取 `fetch_quotes`

**背景**：新浪 HTTP 端点 `https://hq.sinajs.cn/list=<codes>`，**必须带 `Referer: https://finance.sina.com.cn`**，返回 GBK 编码文本，每行对应一个 code。

**Files:**
- Modify: `python/examples/stock_dashboard.py`
- Test: `python/tests/test_stock_dashboard.py`

- [ ] **Step 1: 写失败测试**

追加测试（用 `monkeypatch` mock `requests.get`）：

```python
from unittest.mock import MagicMock

from stock_dashboard import fetch_quotes


class _FakeResp:
    def __init__(self, content: bytes, status: int = 200) -> None:
        self.content = content
        self.status_code = status

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_fetch_quotes_cn_parses_gbk(monkeypatch):
    body = (
        'var hq_str_sh600519="贵州茅台,1630.00,1630.00,1650.00,1660.00,1620.00,a,b";\n'
        'var hq_str_sz000001="平安银行,12.00,12.50,12.45,12.60,12.30,a,b";\n'
    ).encode("gbk")

    fake_get = MagicMock(return_value=_FakeResp(body))
    monkeypatch.setattr("stock_dashboard.requests.get", fake_get)

    result = fetch_quotes(["sh600519", "sz000001"], market="cn")
    assert set(result.keys()) == {"sh600519", "sz000001"}
    assert result["sh600519"]["name"] == "贵州茅台"
    assert result["sz000001"]["price"] == pytest.approx(12.45)

    # 确认带了 Referer 头
    _, kwargs = fake_get.call_args
    assert kwargs["headers"]["Referer"] == "https://finance.sina.com.cn"


def test_fetch_quotes_empty_list_no_request(monkeypatch):
    fake_get = MagicMock()
    monkeypatch.setattr("stock_dashboard.requests.get", fake_get)
    result = fetch_quotes([], market="cn")
    assert result == {}
    fake_get.assert_not_called()


def test_fetch_quotes_request_error_returns_empty(monkeypatch, capsys):
    fake_get = MagicMock(side_effect=RuntimeError("network down"))
    monkeypatch.setattr("stock_dashboard.requests.get", fake_get)
    result = fetch_quotes(["sh600519"], market="cn")
    assert result == {}
    # 错误打到 stderr
    err = capsys.readouterr().err
    assert "network down" in err
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd python && uv run pytest tests/test_stock_dashboard.py::test_fetch_quotes_cn_parses_gbk -v`
Expected: ImportError。

- [ ] **Step 3: 实现**

追加：

```python
import os
import sys
import time
import traceback

import requests

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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd python && uv run pytest tests/test_stock_dashboard.py -v`
Expected: 12 passed。

- [ ] **Step 5: Commit**

```bash
git add python/examples/stock_dashboard.py python/tests/test_stock_dashboard.py
git commit -m "feat: 批量行情获取 fetch_quotes (GBK 解码 + 错误容忍)"
```

---

### Task 6: 格式化辅助函数

**Files:**
- Modify: `python/examples/stock_dashboard.py`
- Test: `python/tests/test_stock_dashboard.py`

- [ ] **Step 1: 写失败测试**

追加：

```python
from stock_dashboard import format_price, format_change_pct


def test_format_price_large():
    assert format_price(1650.0) == "1,650.00"


def test_format_price_small():
    assert format_price(0.1234) == "0.1234"


def test_format_price_zero():
    assert format_price(0.0) == "0"


def test_format_change_pct_positive():
    assert format_change_pct(1.23) == "+1.23%"


def test_format_change_pct_negative():
    assert format_change_pct(-0.80) == "-0.80%"


def test_format_change_pct_zero():
    assert format_change_pct(0.0) == "+0.00%"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd python && uv run pytest tests/test_stock_dashboard.py::test_format_price_large -v`
Expected: ImportError。

- [ ] **Step 3: 实现**

追加：

```python
def format_price(value: float) -> str:
    if value == 0:
        return "0"
    if abs(value) >= 1:
        return f"{value:,.2f}"
    return f"{value:.4g}"


def format_change_pct(pct: float) -> str:
    return f"{pct:+.2f}%"
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd python && uv run pytest tests/test_stock_dashboard.py -v`
Expected: 18 passed。

- [ ] **Step 5: Commit**

```bash
git add python/examples/stock_dashboard.py python/tests/test_stock_dashboard.py
git commit -m "feat: 股票价格/涨跌幅格式化辅助"
```

---

### Task 7: 单个市场的显示行构建 `build_market_rows`

**Files:**
- Modify: `python/examples/stock_dashboard.py`
- Test: `python/tests/test_stock_dashboard.py`

**背景**：把一个市场的 `{code: Quote}` + `codes` 列表转成排好序的 DisplayItem dict 列表。排序规则：解析成功的按 `change_pct` 降序；解析失败的排最后，按 codes 的原始顺序。

- [ ] **Step 1: 写失败测试**

追加：

```python
from stock_dashboard import build_market_rows


def test_build_market_rows_sorted_desc():
    quotes = {
        "a": Quote(name="A", price=10.0, change_pct=1.0),
        "b": Quote(name="B", price=20.0, change_pct=3.5),
        "c": Quote(name="C", price=30.0, change_pct=-2.0),
    }
    rows = build_market_rows(["a", "b", "c"], quotes)
    # 按涨跌幅降序: B(3.5) > A(1.0) > C(-2.0)
    assert [r["label"] for r in rows] == ["B", "A", "C"]


def test_build_market_rows_missing_shown_as_dash():
    quotes = {
        "a": Quote(name="A", price=10.0, change_pct=1.0),
    }
    rows = build_market_rows(["a", "b"], quotes)
    # 解析失败的 'b' 排最后, 显示 '—' 和白色
    assert rows[0]["label"] == "A"
    assert rows[1]["label"] == "b"  # 用原 code 作为名字
    assert rows[1]["cells"] == ["—", "—"]
    assert rows[1]["color"] == "#FFFFFF"


def test_build_market_rows_colors():
    quotes = {
        "up": Quote(name="U", price=1.0, change_pct=2.0),
        "dn": Quote(name="D", price=1.0, change_pct=-1.0),
    }
    rows = build_market_rows(["up", "dn"], quotes)
    assert rows[0]["color"] == "#4CAF50"  # 涨绿
    assert rows[1]["color"] == "#F44336"  # 跌红
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd python && uv run pytest tests/test_stock_dashboard.py::test_build_market_rows_sorted_desc -v`
Expected: ImportError。

- [ ] **Step 3: 实现**

追加：

```python
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd python && uv run pytest tests/test_stock_dashboard.py -v`
Expected: 21 passed。

- [ ] **Step 5: Commit**

```bash
git add python/examples/stock_dashboard.py python/tests/test_stock_dashboard.py
git commit -m "feat: 市场显示行构建与排序 build_market_rows"
```

---

### Task 8: 整体数据组装 `build_data`

**Files:**
- Modify: `python/examples/stock_dashboard.py`

无需单测（整合逻辑，手动验收覆盖）。

- [ ] **Step 1: 实现 build_data**

追加：

```python
def build_data(
    cn_codes: list[str],
    hk_codes: list[str],
    us_codes: list[str],
    refresh_interval: int,
) -> dict:
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
```

- [ ] **Step 2: 确认已有测试仍通过**

Run: `cd python && uv run pytest tests/test_stock_dashboard.py -v`
Expected: 21 passed。

- [ ] **Step 3: Commit**

```bash
git add python/examples/stock_dashboard.py
git commit -m "feat: 整体数据组装 build_data (三市场分段)"
```

---

### Task 9: 配置解析 + `main()` 循环

**Files:**
- Modify: `python/examples/stock_dashboard.py`

- [ ] **Step 1: 在脚本顶部补全 docstring 和环境变量解析**

将 `stock_dashboard.py` 顶部的 docstring 替换为：

```python
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
```

- [ ] **Step 2: 实现环境变量解析和 main**

追加到文件末尾：

```python
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
```

- [ ] **Step 3: 确认现有测试仍通过**

Run: `cd python && uv run pytest tests/test_stock_dashboard.py -v`
Expected: 21 passed（无新增测试，原有仍过）。

- [ ] **Step 4: 确认所有测试都通过（整体回归）**

Run: `cd python && uv run pytest -v`
Expected: 所有测试 pass（包括原来 widget/server 等）。

- [ ] **Step 5: Commit**

```bash
git add python/examples/stock_dashboard.py
git commit -m "feat: stock_dashboard 主入口 (配置解析 + 刷新循环)"
```

---

### Task 10: 手动验收 + README 更新

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 加到 README 的“运行示例”段落**

打开 `README.md`，在 `uv run python examples/binance_dashboard.py` 那行下面新增：

```markdown
uv run python examples/stock_dashboard.py
```

- [ ] **Step 2: 在 README 中追加股票行情示例的环境变量说明**

在"数据格式"表格之前（或文档末尾）追加一小节：

```markdown
## 股票行情示例环境变量

在 `python/.env` 配置以下任一市场（空的市场段不显示）：

```
CN_STOCKS=sh600519,sz000001
HK_STOCKS=00700,09988
US_STOCKS=AAPL,TSLA
REFRESH_INTERVAL=10
```
```

- [ ] **Step 3: 手动验收 - 三市场都配**

前置：`./build.sh` 已构建过 HoverTop.app。在 `python/.env` 加入：

```
CN_STOCKS=sh600519,sz000001
HK_STOCKS=00700,09988
US_STOCKS=AAPL,TSLA
```

Run: `cd python && uv run python examples/stock_dashboard.py`
观察：悬浮窗显示 "股票行情" 标题 + 三段（A股/港股/美股），每段有橙色表头和若干股票行，每行 "名称  价格  涨跌幅"。10 秒刷新一次。`Ctrl+C` 能干净退出。

- [ ] **Step 4: 手动验收 - 只配 A股**

临时把 .env 里的 HK_STOCKS / US_STOCKS 清空或注释。
Run: `uv run python examples/stock_dashboard.py`
观察：只显示 A股 段，无港股/美股段。

- [ ] **Step 5: 手动验收 - 无效代码**

`CN_STOCKS=sh600519,sh999999`
Run: 观察 sh999999 显示 `—`，sh600519 正常。不崩溃。

- [ ] **Step 6: 手动验收 - DEBUG 模式**

Run: `DEBUG=1 uv run python examples/stock_dashboard.py`（短暂断网或改个错配置）
观察：stderr 有完整 traceback。

- [ ] **Step 7: Commit**

```bash
git add README.md
git commit -m "docs: README 增加 stock_dashboard 运行说明"
```

---

## 完成标准

- [ ] 所有测试通过：`cd python && uv run pytest`
- [ ] 手动验收 3 种场景都符合预期
- [ ] 无新增第三方依赖（`pyproject.toml` 未变）
- [ ] 所有 commit 都原子、消息清晰
