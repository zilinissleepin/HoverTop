"""币安仪表盘悬浮窗 - 行情 + 持仓

板块一: 现货/合约/Alpha 代币价格及涨跌幅
板块二: 账户持仓总值及各标的持仓价值

每 10 秒刷新一次。

环境变量配置方式:

  # 1. 直接在终端设置 (当前会话有效)
  export TOKEN_AMOUNTS="BTC:0.5,SOL:10.0,VIRTUAL:1000"
  export BINANCE_API_KEY="your_api_key"
  export BINANCE_SECRET_KEY="your_secret_key"
  export BINANCE_COOKIE="p20t=...; cr00=..."
  export BINANCE_CSRFTOKEN="your_csrf_token"

  # 2. 使用 .env 文件 (推荐)
  # 在 python/ 目录下创建 .env 文件，内容:
  TOKEN_AMOUNTS=BTC:0.5,SOL:10.0,VIRTUAL:1000
  BINANCE_API_KEY=your_api_key
  BINANCE_SECRET_KEY=your_secret_key
  BINANCE_COOKIE=p20t=...; cr00=...
  BINANCE_CSRFTOKEN=your_csrf_token

  # 3. 不配置环境变量
  # 仅显示行情，不显示持仓

环境变量说明:
  TOKEN_AMOUNTS      - 代币数量，格式: "BTC:0.5,SOL:10" (优先使用，不查 API)
  BINANCE_API_KEY    - 币安 API Key (查询现货/合约余额)
  BINANCE_SECRET_KEY - 币安 API Secret
  BINANCE_COOKIE     - 币安网页 Cookie (查询 Alpha 持仓)
  BINANCE_CSRFTOKEN  - 币安 CSRF Token (查询 Alpha 持仓)

获取 API 密钥: https://www.binance.com/zh-CN/my/settings/api-management
获取 Cookie:    登录 binance.com → F12 → Application → Cookies

调用方式: uv run python examples/binance_dashboard.py
"""

import gzip
import json
import os
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from hovertop import Widget

# 自动加载 python/.env 文件
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# ============ 配置区域 ============

# 现货行情监控列表 (格式: 'BTCUSDT')
SPOT_SYMBOLS = ["VIRTUALUSDT"]

# 合约行情监控列表 (格式: 'BTCUSDT')
FUTURES_SYMBOLS = ["BTCUSDT", "SOLUSDT"]

# Alpha 代币监控列表 (格式: 'SENTIS')
ALPHA_TOKENS = ["SENTIS"]

# 现货持仓代币列表 (用于查询持仓数量)
SPOT_TOKENS = ["BTC", "SOL", "VIRTUAL"]

# 代币数量配置 (直接指定数量，跳过 API 查询)
# 环境变量格式: export TOKEN_AMOUNTS="BTC:0.5,SOL:10.0,VIRTUAL:1000"
_token_raw = os.environ.get("TOKEN_AMOUNTS", "")
TOKEN_AMOUNTS: dict[str, float] = {}
if _token_raw:
    for pair in _token_raw.split(","):
        if ":" in pair:
            sym, amt = pair.split(":", 1)
            try:
                TOKEN_AMOUNTS[sym.strip().upper()] = float(amt.strip())
            except ValueError:
                pass

# 币安 API 密钥 (用于查询现货/合约持仓)
# 获取地址: https://www.binance.com/zh-CN/my/settings/api-management
# 设置方式: export BINANCE_API_KEY="your_key"
API_KEY = os.environ.get("BINANCE_API_KEY", "")
SECRET_KEY = os.environ.get("BINANCE_SECRET_KEY", "")

# 币安网页 Cookie (用于查询 Alpha 持仓)
# 获取方式: 登录 binance.com → F12 → Application → Cookies
# 需要字段: p20t, cr00, s9r1, d1og, logined
# 设置方式: export BINANCE_COOKIE="p20t=...; cr00=..."
BINANCE_COOKIE = os.environ.get("BINANCE_COOKIE", "")
BINANCE_CSRFTOKEN = os.environ.get("BINANCE_CSRFTOKEN", "")

# 刷新间隔 (秒)
REFRESH_INTERVAL = 10

# =================================


def get_json(url: str, headers: dict | None = None) -> dict:
    """请求 URL 并返回 JSON，支持 gzip 解压"""
    req_headers = {"User-Agent": "Mozilla/5.0", "Accept-Encoding": "gzip"}
    if headers:
        req_headers.update(headers)
    req = Request(url, headers=req_headers)
    with urlopen(req, timeout=10) as response:
        content = response.read()
        if response.info().get("Content-Encoding") == "gzip":
            content = gzip.decompress(content)
        return json.loads(content)


def format_number(value: float) -> str:
    """统一数值格式: >=1 保留 2 位小数, <1 保留 4 位有效数字"""
    if value == 0:
        return "0"
    if abs(value) >= 1:
        return f"{value:,.2f}"
    return f"{value:.4g}"


def format_value(value: float) -> str:
    """格式化美元金额: 前缀 $ + 统一数值格式"""
    return f"${format_number(value)}"


# --- 现货行情 ---


def fetch_spot_prices(symbols: list[str]) -> dict[str, dict]:
    """获取现货 24h 行情"""
    result = {}
    for symbol in symbols:
        try:
            url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
            data = get_json(url)
            name = symbol.replace("USDT", "").replace("USDC", "")
            result[name] = {
                "price": format_number(float(data["lastPrice"])),
                "change": data["priceChangePercent"],
            }
        except Exception:
            pass
    return result


# --- 合约行情 ---


def fetch_futures_prices(symbols: list[str]) -> dict[str, dict]:
    """获取合约 24h 行情"""
    result = {}
    for symbol in symbols:
        try:
            url = f"https://fapi.binance.com/fapi/v1/ticker/24hr?symbol={symbol}"
            data = get_json(url)
            name = symbol.replace("USDT", "").replace("USDC", "")
            result[name] = {
                "price": format_number(float(data["lastPrice"])),
                "change": data["priceChangePercent"],
            }
        except Exception:
            pass
    return result


# --- Alpha 代币 ---


def fetch_alpha_prices(tokens: list[str]) -> dict[str, dict]:
    """批量获取 Alpha 代币价格及涨跌幅

    返回: {symbol: {'price': float, 'change': float | None}}
    涨跌幅字段在不同版本 API 中可能缺失，此时为 None。
    """
    result: dict[str, dict] = {}
    if not tokens:
        return result
    try:
        url = "https://www.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/cex/alpha/all/token/list"
        data = get_json(url)
        if data.get("code") == "000000":
            for token in data.get("data", []):
                sym = token.get("symbol")
                if sym not in tokens:
                    continue
                # 尝试多个常见字段名取涨跌幅
                raw_change = (
                    token.get("percentChange24h")
                    or token.get("priceChangePercent")
                    or token.get("change24h")
                )
                try:
                    change = float(raw_change) if raw_change is not None else None
                except (TypeError, ValueError):
                    change = None
                result[sym] = {
                    "price": float(token.get("price", 0)),
                    "change": change,
                }
    except Exception:
        pass
    return result


# --- 持仓查询 ---


def make_signed_request(url: str, params: dict | None = None) -> dict:
    """发送带签名的币安 API 请求"""
    import hashlib
    import hmac as hmac_mod

    if params is None:
        params = {}
    params["timestamp"] = int(time.time() * 1000)
    query_string = urlencode(params)
    signature = hmac_mod.new(
        SECRET_KEY.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    params["signature"] = signature
    full_url = f"{url}?{urlencode(params)}"
    req = Request(full_url, headers={"X-MBX-APIKEY": API_KEY, "User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=10) as response:
        return json.loads(response.read())


def get_spot_balances() -> dict[str, float] | None:
    """获取现货账户余额"""
    try:
        data = make_signed_request("https://api.binance.com/api/v3/account")
        balances = {}
        for b in data.get("balances", []):
            total = float(b["free"]) + float(b["locked"])
            if total > 0:
                balances[b["asset"]] = total
        return balances
    except Exception:
        return None


def get_futures_balances() -> dict[str, float] | None:
    """获取合约账户余额"""
    try:
        data = make_signed_request("https://fapi.binance.com/fapi/v2/account")
        balances = {}
        for asset in data.get("assets", []):
            wb = float(asset["walletBalance"])
            if wb > 0:
                balances[asset["asset"]] = wb
        return balances
    except Exception:
        return None


def get_alpha_holdings() -> dict[str, dict] | None:
    """获取 Alpha 代币持仓 (需要 Cookie 认证)

    返回: {symbol: {'amount': float, 'valuation': float}} 或 None
    """
    if not BINANCE_COOKIE or not BINANCE_CSRFTOKEN:
        return None
    try:
        url = "https://www.binance.com/bapi/defi/v1/private/wallet-direct/cloud-wallet/alpha"
        req = Request(url, headers={
            "clienttype": "web",
            "content-type": "application/json",
            "csrftoken": BINANCE_CSRFTOKEN,
            "user-agent": "Mozilla/5.0",
            "Cookie": BINANCE_COOKIE,
        })
        with urlopen(req, timeout=10) as response:
            data = json.loads(response.read())

        if data.get("code") != "000000":
            return None

        holdings: dict[str, dict] = {}
        for item in data.get("data", {}).get("list", []):
            sym = item.get("symbol", "")
            amount = float(item.get("amount", 0))
            valuation = float(item.get("valuation", 0))
            if amount > 0:
                holdings[sym] = {"amount": amount, "valuation": valuation}
        return holdings
    except Exception:
        return None


def get_token_prices() -> dict[str, float] | None:
    """获取所有 USDT 计价的代币价格"""
    try:
        url = "https://api.binance.com/api/v3/ticker/price"
        data = get_json(url)
        prices = {}
        for item in data:
            sym = item["symbol"]
            if sym.endswith("USDT"):
                prices[sym[:-4]] = float(item["price"])
        return prices
    except Exception:
        return None


def calculate_spot_value(
    tokens: list[str],
    spot_balances: dict[str, float] | None,
    prices: dict[str, float] | None,
) -> float:
    """计算现货持仓总值"""
    if prices is None:
        return 0.0
    total = 0.0
    for token in tokens:
        if token in TOKEN_AMOUNTS:
            total += TOKEN_AMOUNTS[token] * prices.get(token, 0)
        elif spot_balances and token in spot_balances:
            total += spot_balances[token] * prices.get(token, 0)
    return total


def calculate_futures_value(
    futures_balances: dict[str, float] | None,
) -> float:
    """计算合约账户 USDT 余额"""
    if futures_balances is None:
        return 0.0
    return futures_balances.get("USDT", 0)


def calculate_alpha_value(
    alpha_holdings: dict[str, dict] | None,
    tokens: list[str],
) -> float:
    """计算 Alpha 持仓总值"""
    if alpha_holdings is None:
        return 0.0
    total = 0.0
    for token in tokens:
        if token in alpha_holdings:
            total += alpha_holdings[token]["valuation"]
    return total


def color_for_change(change: float) -> str:
    """涨跌颜色: 涨绿跌红"""
    return "#4CAF50" if change >= 0 else "#F44336"


def build_data() -> dict:
    """构建悬浮窗展示数据 - 单板块四列布局

    每行 cells = [价格, 涨跌幅, 持仓价值]，由 Swift 端按列宽渲染对齐
    """
    DASH = "—"

    def fmt_price(price: str | float | None) -> str:
        if price is None or price == "":
            return DASH
        return price if isinstance(price, str) else format_number(float(price))

    def fmt_change(change: float | None) -> str:
        if change is None:
            return DASH
        return f"{change:+.2f}%"

    def fmt_hold(value: float | None) -> str:
        if value is None or value <= 0:
            return DASH
        return format_value(value)

    # ── 收集行情 ──
    spot_market = fetch_spot_prices(SPOT_SYMBOLS)
    futures_market = fetch_futures_prices(FUTURES_SYMBOLS)
    alpha_market = fetch_alpha_prices(ALPHA_TOKENS)

    # ── 收集持仓 ──
    has_manual_amounts = bool(TOKEN_AMOUNTS)
    has_api_keys = bool(API_KEY and SECRET_KEY)
    has_holdings = has_manual_amounts or has_api_keys

    spot_balances = get_spot_balances() if has_api_keys else None
    futures_balances = get_futures_balances() if has_api_keys else None
    spot_prices_map = get_token_prices() if has_holdings else None
    alpha_holdings = get_alpha_holdings() if (has_holdings and ALPHA_TOKENS) else None

    spot_total = calculate_spot_value(SPOT_TOKENS, spot_balances, spot_prices_map) if has_holdings else 0.0
    futures_total = calculate_futures_value(futures_balances) if has_holdings else 0.0
    alpha_total = calculate_alpha_value(alpha_holdings, ALPHA_TOKENS) if has_holdings else 0.0
    grand_total = spot_total + futures_total + alpha_total

    items = []

    # ── 表头 + 总值 (始终置顶) ──
    total_text = format_value(grand_total) if has_holdings else DASH
    items.append({
        "label": "总值",
        "value": "",
        "color": "#FF9800",
        "cells": ["", "", total_text],
    })

    # ── 收集所有数据行 (待排序) ──
    # 每个元素: (持仓价值, 行 dict)
    rows: list[tuple[float, dict]] = []
    spot_names = {s.replace("USDT", "").replace("USDC", "") for s in SPOT_SYMBOLS}

    def add_row(name: str, price: str | float | None, change: float | None,
                hold_val: float | None, color: str) -> None:
        rows.append((
            hold_val or 0.0,
            {
                "label": name,
                "value": "",
                "color": color,
                "cells": [fmt_price(price), fmt_change(change), fmt_hold(hold_val)],
            },
        ))

    # 现货行情/持仓
    for symbol in SPOT_SYMBOLS:
        name = symbol.replace("USDT", "").replace("USDC", "")
        info = spot_market.get(name)
        price = info["price"] if info else None
        change = float(info["change"]) if info and info["change"] else (0.0 if info else None)
        color = color_for_change(change) if change is not None else "#FFFFFF"

        hold_val: float | None = None
        if has_holdings and spot_prices_map:
            unit_price = spot_prices_map.get(name, 0)
            if name in TOKEN_AMOUNTS:
                hold_val = TOKEN_AMOUNTS[name] * unit_price
            elif spot_balances and name in spot_balances:
                hold_val = spot_balances[name] * unit_price
        add_row(name, price, change, hold_val, color)

    # 合约行情/持仓 (现货同名代币不再重复计算持仓)
    for symbol in FUTURES_SYMBOLS:
        name = symbol.replace("USDT", "").replace("USDC", "")
        info = futures_market.get(name)
        price = info["price"] if info else None
        change = float(info["change"]) if info and info["change"] else (0.0 if info else None)
        color = color_for_change(change) if change is not None else "#FFFFFF"

        hold_val = None
        if has_holdings and spot_prices_map and name not in spot_names:
            unit_price = spot_prices_map.get(name, 0)
            if name in TOKEN_AMOUNTS:
                hold_val = TOKEN_AMOUNTS[name] * unit_price
            elif spot_balances and name in spot_balances:
                hold_val = spot_balances[name] * unit_price
        add_row(name, price, change, hold_val, color)

    # Alpha 行情/持仓
    for token in ALPHA_TOKENS:
        info = alpha_market.get(token)
        price = info["price"] if info else None
        change = info["change"] if info else None
        color = color_for_change(change) if change is not None else "#FFFFFF"

        hold_val = None
        if alpha_holdings and token in alpha_holdings:
            hold_val = alpha_holdings[token]["valuation"]
        add_row(token, price, change, hold_val, color)

    # 合约 USDT 余额 (无价格无涨跌，仅持仓)
    if has_holdings and futures_total > 0:
        rows.append((
            futures_total,
            {
                "label": "合约USDT",
                "value": "",
                "color": "#FFFFFF",
                "cells": [DASH, DASH, fmt_hold(futures_total)],
            },
        ))

    # ── 按持仓价值降序排序后追加 ──
    rows.sort(key=lambda r: r[0], reverse=True)
    items.extend(row for _, row in rows)

    return {
        "title": "币安仪表盘",
        "subtitle": time.strftime("%H:%M:%S"),
        "items": items,
        "footer": f"每 {REFRESH_INTERVAL} 秒刷新 | Ctrl+C 退出",
    }


def main() -> None:
    with Widget("币安仪表盘") as widget:
        print("币安仪表盘悬浮窗已启动，按 Ctrl+C 退出...")
        while True:
            try:
                widget.update(**build_data())
            except Exception as e:
                widget.update(
                    title="币安仪表盘",
                    subtitle="数据获取失败",
                    items=[{"label": "错误", "value": str(e)[:50], "color": "#F44336"}],
                )
            time.sleep(REFRESH_INTERVAL)


if __name__ == "__main__":
    main()
