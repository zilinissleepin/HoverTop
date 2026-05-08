"""币安仪表盘悬浮窗 - 行情 + 持仓 + 合约浮盈

布局:
  主表 (按持仓价值降序): 总值 + 现货 + Alpha 各代币的价格/涨跌幅/持仓
  合约板块: 每个合约头寸的当前价/涨跌幅/浮盈浮亏 (按浮盈绝对值降序)

每 10 秒刷新一次。

必填环境变量 (代币列表, 直接用 TOKEN, 不带 USDT 后缀):
  SPOT_TOKENS    - 现货行情/持仓代币, 逗号分隔. 例: "VIRTUAL,BTC"
  FUTURES_TOKENS - 合约行情/持仓代币, 逗号分隔. 例: "BTC,SOL"
  ALPHA_TOKENS   - Alpha 代币行情/持仓, 逗号分隔. 例: "SENTIS,B2"

可选环境变量 (持仓查询):
  TOKEN_AMOUNTS      - 现货代币数量, 跳过 API 查询. 例: "BTC:0.5,SOL:10"
  BINANCE_API_KEY    - 币安 API Key (查询现货余额 + 合约持仓)
  BINANCE_SECRET_KEY - 币安 API Secret
  BINANCE_COOKIE     - 币安网页 Cookie (查询 Alpha 持仓)
  BINANCE_CSRFTOKEN  - 币安 CSRF Token

.env 示例 (放在 python/.env):
  SPOT_TOKENS=VIRTUAL
  FUTURES_TOKENS=BTC,SOL
  ALPHA_TOKENS=SENTIS
  BINANCE_API_KEY=your_api_key
  BINANCE_SECRET_KEY=your_secret_key
  BINANCE_COOKIE=p20t=...; cr00=...
  BINANCE_CSRFTOKEN=your_csrf_token

获取 API 密钥: https://www.binance.com/zh-CN/my/settings/api-management
获取 Cookie:    登录 binance.com → F12 → Application → Cookies

调用方式: uv run python examples/binance_dashboard.py
"""

import hashlib
import hmac as hmac_mod
import os
import sys
import time
import traceback

import requests
from dotenv import load_dotenv
from hovertop import Widget


def log_err(where: str, exc: BaseException) -> None:
    """打印错误到 stderr，包含调用位置和异常类型"""
    print(f"[{time.strftime('%H:%M:%S')}] {where}: {type(exc).__name__}: {exc}", file=sys.stderr)
    # 仅在调试模式下打印完整 traceback
    if os.environ.get("DEBUG"):
        traceback.print_exc(file=sys.stderr)

# 自动加载 python/.env 文件
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


def _parse_token_list(env_name: str) -> list[str]:
    """解析逗号分隔的代币列表环境变量"""
    raw = os.environ.get(env_name, "")
    return [s.strip().upper() for s in raw.split(",") if s.strip()]


def to_symbol(token: str) -> str:
    """代币名转 USDT 计价的交易对 symbol"""
    return f"{token}USDT"


# ============ 配置区域 (全部从环境变量读取) ============

# 现货代币列表 (格式: 'BTC')
SPOT_TOKENS = _parse_token_list("SPOT_TOKENS")

# 合约代币列表 (格式: 'BTC')
FUTURES_TOKENS = _parse_token_list("FUTURES_TOKENS")

# Alpha 代币列表 (格式: 'SENTIS')
ALPHA_TOKENS = _parse_token_list("ALPHA_TOKENS")

# 现货代币数量配置 (直接指定，跳过 API 查询)
# 环境变量格式: TOKEN_AMOUNTS="BTC:0.5,SOL:10.0,VIRTUAL:1000"
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

# 币安 API 密钥 (用于查询现货余额 + 合约持仓)
API_KEY = os.environ.get("BINANCE_API_KEY", "")
SECRET_KEY = os.environ.get("BINANCE_SECRET_KEY", "")

# 币安网页 Cookie (用于查询 Alpha 持仓)
BINANCE_COOKIE = os.environ.get("BINANCE_COOKIE", "")
BINANCE_CSRFTOKEN = os.environ.get("BINANCE_CSRFTOKEN", "")

# 刷新间隔 (秒)
REFRESH_INTERVAL = 10

# =================================


def get_json(url: str, headers: dict | None = None, timeout: int = 15) -> dict:
    """请求 URL 并返回 JSON"""
    req_headers = {"User-Agent": "Mozilla/5.0"}
    if headers:
        req_headers.update(headers)
    resp = requests.get(url, headers=req_headers, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


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
        except Exception as e:
            log_err(f"fetch_spot_prices({symbol})", e)
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
        except Exception as e:
            log_err(f"fetch_futures_prices({symbol})", e)
    return result


# --- Alpha 代币 ---


def fetch_alpha_prices(tokens: list[str]) -> dict[str, dict]:
    """批量获取 Alpha 代币价格及涨跌幅

    返回: {symbol: {'price': float, 'change': float | None}}
    涨跌幅字段在不同版本 API 中可能缺失，此时为 None。

    该 endpoint 偶发慢响应, 自动重试最多 3 次。
    """
    result: dict[str, dict] = {}
    if not tokens:
        return result
    url = "https://www.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/cex/alpha/all/token/list"

    last_err: Exception | None = None
    for attempt in range(3):
        try:
            data = get_json(url, timeout=20)
            last_err = None
            break
        except Exception as e:
            last_err = e
            if attempt < 2:
                time.sleep(0.5 * (attempt + 1))  # 0.5s, 1s 退避

    if last_err is not None:
        log_err(f"fetch_alpha_prices (after 3 retries)", last_err)
        return result

    try:
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
    except Exception as e:
        log_err("fetch_alpha_prices (parse)", e)
    return result


# --- 持仓查询 ---


def make_signed_request(
    url: str,
    params: dict | None = None,
    timeout: int = 20,
    retries: int = 2,
) -> dict:
    """发送带签名的币安 API 请求

    - 自动重试 (默认共 3 次): 网络超时时退避后重试
    - HTTP 4xx/5xx 不重试, 直接抛出含响应体的异常
    """
    last_err: Exception | None = None
    for attempt in range(retries + 1):
        # 每次重新算 timestamp+签名 (避免时间戳过期)
        local_params = dict(params) if params else {}
        local_params["timestamp"] = int(time.time() * 1000)
        local_params.setdefault("recvWindow", 10000)
        query_string = "&".join(f"{k}={v}" for k, v in local_params.items())
        signature = hmac_mod.new(
            SECRET_KEY.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        local_params["signature"] = signature
        try:
            resp = requests.get(
                url,
                params=local_params,
                headers={"X-MBX-APIKEY": API_KEY, "User-Agent": "Mozilla/5.0"},
                timeout=timeout,
            )
            if resp.status_code >= 400:
                raise requests.HTTPError(
                    f"HTTP {resp.status_code} | body={resp.text}", response=resp
                )
            return resp.json()
        except requests.HTTPError:
            raise
        except (requests.Timeout, requests.ConnectionError, OSError) as e:
            last_err = e
            if attempt < retries:
                time.sleep(0.5 * (attempt + 1))

    assert last_err is not None
    raise last_err


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
    except Exception as e:
        log_err("get_spot_balances", e)
        return None


def get_futures_positions() -> dict[str, dict] | None:
    """获取合约持仓 (按 symbol 分项)

    返回: {symbol: {'amount': float, 'entry': float, 'pnl': float}} 或 None
      - amount: 持仓张数 (正=多, 负=空)
      - entry:  开仓均价
      - pnl:    未实现盈亏 (USDT)

    使用 /fapi/v3/positionRisk: 只返回有持仓的 symbol, 响应体小、速度快;
    /fapi/v2/account 返回全部 symbol (几百个), 容易触发读超时。
    """
    try:
        data = make_signed_request("https://fapi.binance.com/fapi/v3/positionRisk")
        # v3/positionRisk 返回列表; 防御性处理: 也支持 dict 包裹格式
        rows = data if isinstance(data, list) else data.get("positions", [])
        positions: dict[str, dict] = {}
        for p in rows:
            amt = float(p.get("positionAmt", 0))
            if amt == 0:
                continue
            sym = p.get("symbol", "")
            # 不同端点字段名: unRealizedProfit (v3) / unrealizedProfit (v2)
            pnl = p.get("unRealizedProfit") or p.get("unrealizedProfit") or 0
            positions[sym] = {
                "amount": amt,
                "entry": float(p.get("entryPrice", 0)),
                "pnl": float(pnl),
            }
        return positions
    except Exception as e:
        log_err("get_futures_positions", e)
        return None


def get_alpha_holdings() -> dict[str, dict] | None:
    """获取 Alpha 代币持仓 (需要 Cookie 认证)

    返回: {symbol: {'amount': float, 'valuation': float}} 或 None
    """
    if not BINANCE_COOKIE or not BINANCE_CSRFTOKEN:
        return None
    try:
        url = "https://www.binance.com/bapi/defi/v1/private/wallet-direct/cloud-wallet/alpha"
        resp = requests.get(url, headers={
            "clienttype": "web",
            "content-type": "application/json",
            "csrftoken": BINANCE_CSRFTOKEN,
            "user-agent": "Mozilla/5.0",
            "Cookie": BINANCE_COOKIE,
        }, timeout=15)
        resp.raise_for_status()
        data = resp.json()

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
    except Exception as e:
        log_err("get_alpha_holdings", e)
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
    except Exception as e:
        log_err("get_token_prices", e)
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
        if spot_balances and token in spot_balances:
            total += spot_balances[token] * prices.get(token, 0)
        elif token in TOKEN_AMOUNTS:
            total += TOKEN_AMOUNTS[token] * prices.get(token, 0)
    return total


def calculate_alpha_value(
    alpha_holdings: dict[str, dict] | None,
    tokens: list[str],
    market: dict[str, dict] | None,
) -> float:
    """计算 Alpha 持仓总值"""
    total = 0.0
    for token in tokens:
        if alpha_holdings and token in alpha_holdings:
            total += alpha_holdings[token]["valuation"]
        elif token in TOKEN_AMOUNTS:
            total += TOKEN_AMOUNTS[token] * market.get(token, {}).get("price", 0) if market else 0
    return total


def color_for_change(change: float) -> str:
    """涨跌颜色: 涨绿跌红"""
    return "#4CAF50" if change >= 0 else "#F44336"


def color_for_pnl(pnl: float) -> str:
    """浮盈浮亏颜色: 盈绿亏红, 0 白色"""
    if pnl > 0:
        return "#4CAF50"
    if pnl < 0:
        return "#F44336"
    return "#FFFFFF"


def build_data() -> dict:
    """构建悬浮窗展示数据

    布局:
      主表:    总值 + (现货/Alpha 各代币 行情+持仓), 按持仓价值降序
      合约板块: 各合约头寸 行情+浮盈浮亏, 按浮盈绝对值降序

    每行 cells = [价格, 涨跌幅, 持仓价值/浮盈]
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

    def fmt_pnl(pnl: float) -> str:
        """浮盈浮亏: 带 +/- 符号, $ 前缀"""
        sign = "+" if pnl >= 0 else "-"
        return f"{sign}${format_number(abs(pnl))}"

    # ── 收集行情 ──
    spot_market = fetch_spot_prices([to_symbol(t) for t in SPOT_TOKENS])
    futures_market = fetch_futures_prices([to_symbol(t) for t in FUTURES_TOKENS])
    alpha_market = fetch_alpha_prices(ALPHA_TOKENS)

    # ── 收集持仓 ──
    has_manual_amounts = bool(TOKEN_AMOUNTS)
    has_api_keys = bool(API_KEY and SECRET_KEY)
    has_holdings = has_manual_amounts or has_api_keys

    spot_balances = get_spot_balances() if has_api_keys else None
    futures_positions = get_futures_positions() if has_api_keys else None
    spot_prices_map = get_token_prices() if has_holdings else None
    # alpha_holdings = get_alpha_holdings() if (has_holdings and ALPHA_TOKENS) else None
    alpha_holdings = None

    spot_total = calculate_spot_value(SPOT_TOKENS, spot_balances, spot_prices_map) if has_holdings else 0.0
    alpha_total = calculate_alpha_value(alpha_holdings, ALPHA_TOKENS, alpha_market) if has_holdings else 0.0

    # 合约浮盈累加
    futures_pnl_total = 0.0
    if futures_positions:
        futures_pnl_total = sum(p["pnl"] for p in futures_positions.values())
    
    grand_total = spot_total + alpha_total

    items = []

    # ── 表头 + 总值 (始终置顶) ──
    total_text = format_value(grand_total) if has_holdings else DASH
    items.append({
        "label": "现货/Alpha",
        "value": "",
        "color": "#FF9800",
        "cells": ["", "", total_text],
    })

    # ── 主表数据行 (现货 + Alpha, 按持仓价值降序) ──
    rows: list[tuple[float, dict]] = []

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

    # 现货
    for name in SPOT_TOKENS:
        info = spot_market.get(name)
        price = info["price"] if info else None
        change = float(info["change"]) if info and info["change"] else (0.0 if info else None)
        color = color_for_change(change) if change is not None else "#FFFFFF"

        hold_val: float | None = None
        if has_holdings and spot_prices_map:
            unit_price = spot_prices_map.get(name, 0)
            if spot_balances and name in spot_balances:
                hold_val = spot_balances[name] * unit_price
            elif name in TOKEN_AMOUNTS:
                hold_val = TOKEN_AMOUNTS[name] * unit_price
        add_row(name, price, change, hold_val, color)

    # Alpha
    for token in ALPHA_TOKENS:
        info = alpha_market.get(token)
        price = info["price"] if info else None
        change = info["change"] if info else None
        color = color_for_change(change) if change is not None else "#FFFFFF"

        hold_val = None
        if alpha_holdings and token in alpha_holdings:
            hold_val = alpha_holdings[token]["valuation"]
        elif token in TOKEN_AMOUNTS:
            hold_val = TOKEN_AMOUNTS[token] * alpha_market.get(token, {}).get("price", 0) if alpha_market else 0
        add_row(token, price, change, hold_val, color)

    rows.sort(key=lambda r: r[0], reverse=True)
    items.extend(row for _, row in rows)

    # ── 合约板块 (按浮盈绝对值降序) ──
    futures_rows: list[tuple[float, dict]] = []
    for name in FUTURES_TOKENS:
        symbol = to_symbol(name)
        info = futures_market.get(name)
        price = info["price"] if info else None
        change = float(info["change"]) if info and info["change"] else (0.0 if info else None)

        pos = futures_positions.get(symbol) if futures_positions else None
        if pos:
            pnl = pos["pnl"]
            pnl_text = fmt_pnl(pnl)
            color = color_for_pnl(pnl)
            sort_key = pnl
        else:
            pnl_text = DASH
            color = color_for_change(change) if change is not None else "#FFFFFF"
            sort_key = 0.0

        futures_rows.append((
            sort_key,
            {
                "label": f"PERP {name}",
                "value": "",
                "color": color,
                "cells": [fmt_price(price), fmt_change(change), pnl_text],
            },
        ))

    if futures_rows:
        # 合约板块表头 (与"总值"行风格一致, 但显示合约浮盈合计)
        futures_total_text = fmt_pnl(futures_pnl_total) if futures_positions else DASH
        items.append({
            "label": "合约",
            "value": "",
            # "color": color_for_pnl(futures_pnl_total) if futures_positions else "#FF9800",
            "color": "#FF9800",
            "cells": ["", "", futures_total_text],
        })
        futures_rows.sort(key=lambda r: r[0], reverse=True)
        items.extend(row for _, row in futures_rows)

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
                log_err("build_data/update", e)
                widget.update(
                    title="币安仪表盘",
                    subtitle="数据获取失败",
                    items=[{"label": "错误", "value": str(e)[:50], "color": "#F44336"}],
                )
            time.sleep(REFRESH_INTERVAL)


if __name__ == "__main__":
    main()
