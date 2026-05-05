"""币安仪表盘悬浮窗示例 - 合约价格 + Alpha 代币 + 持仓总值

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
  # 仅显示合约行情和 Alpha 代币价格，不显示持仓

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
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from hovertop import Widget

# 自动加载 python/.env 文件
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# ============ 配置区域 ============

# 合约行情监控列表 (格式: 'BTCUSDT')
FUTURES_SYMBOLS = ["BTCUSDT", "SOLUSDT"]

# Alpha 代币监控列表 (格式: 'SENTIS')
ALPHA_TOKENS = ["SENTIS"]

# 持仓监控 - 现货代币列表
PORTFOLIO_TOKENS = ["BTC", "SOL", "VIRTUAL"]

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


def format_price(price_str: str) -> str:
    """去除价格字符串末尾多余的零"""
    if "." in price_str:
        return price_str.rstrip("0").rstrip(".")
    return price_str


def format_amount(value: float) -> str:
    """格式化数量: 4 位有效数字"""
    if value >= 1000:
        return f"{value:,.0f}"
    elif value >= 1:
        return f"{value:.4g}"
    else:
        return f"{value:.4g}"


def format_value(value: float) -> str:
    """格式化金额: 小数点后 2 位"""
    if value >= 1000:
        return f"${value:,.2f}"
    else:
        return f"${value:.2f}"


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
                "price": format_price(data["lastPrice"]),
                "change": data["priceChangePercent"],
            }
        except Exception:
            pass
    return result


# --- Alpha 代币 ---


def fetch_alpha_prices(tokens: list[str]) -> dict[str, float]:
    """批量获取 Alpha 代币价格"""
    prices: dict[str, float] = {}
    if not tokens:
        return prices
    try:
        url = "https://www.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/cex/alpha/all/token/list"
        data = get_json(url)
        if data.get("code") == "000000":
            for token in data.get("data", []):
                sym = token.get("symbol")
                if sym in tokens:
                    prices[sym] = float(token.get("price", 0))
    except Exception:
        pass
    return prices


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


def calculate_portfolio(
    tokens: list[str],
    spot_balances: dict[str, float] | None,
    futures_balances: dict[str, float] | None,
    prices: dict[str, float] | None,
) -> tuple[float, list[tuple[str, float, float]]]:
    """计算持仓总值，返回 (总值, [(代币, 数量, 价值)])

    如果 TOKEN_AMOUNTS 中配置了某个代币的数量，直接使用，不查询 API。
    """
    if prices is None:
        return 0, []

    total = 0.0
    details: list[tuple[str, float, float]] = []

    for token in tokens:
        value = 0.0
        amount = 0.0

        # 优先使用手动配置的数量
        if token in TOKEN_AMOUNTS:
            amount = TOKEN_AMOUNTS[token]
            if token in prices:
                value = amount * prices[token]
        else:
            if spot_balances and token in spot_balances:
                amt = spot_balances[token]
                if token in prices:
                    value += amt * prices[token]
                    amount += amt

            if token == "USDT" and futures_balances and "USDT" in futures_balances:
                amt = futures_balances["USDT"]
                value += amt
                amount += amt

        if value > 0:
            total += value
            details.append((token, amount, value))

    return total, details


def build_data() -> dict:
    """构建悬浮窗展示数据"""
    items = []

    # ── 上方: 行情 (价格 + 涨跌幅) ──
    futures = fetch_futures_prices(FUTURES_SYMBOLS)
    for name, info in futures.items():
        change = float(info["change"]) if info["change"] else 0
        color = "#4CAF50" if change >= 0 else "#F44336"
        items.append({
            "label": f"{name}",
            "value": f"{info['price']}  {change:+.2f}%",
            "color": color,
        })

    alpha_prices = fetch_alpha_prices(ALPHA_TOKENS)
    for token in ALPHA_TOKENS:
        price = alpha_prices.get(token, 0)
        items.append({
            "label": f"α{token}",
            "value": f"{format_value(price)}",
            "color": "#FF9800",
        })

    # ── 下方: 持仓 (美元价值) ──
    has_manual_amounts = bool(TOKEN_AMOUNTS)
    has_api_keys = bool(API_KEY and SECRET_KEY)
    if has_manual_amounts or has_api_keys:
        spot = get_spot_balances() if has_api_keys else None
        futures_bal = get_futures_balances() if has_api_keys else None
        prices = get_token_prices()
        total, details = calculate_portfolio(PORTFOLIO_TOKENS, spot, futures_bal, prices)

        alpha_holdings = get_alpha_holdings() if ALPHA_TOKENS else None
        alpha_total = 0.0
        if alpha_holdings:
            for token in ALPHA_TOKENS:
                if token in alpha_holdings:
                    h = alpha_holdings[token]
                    alpha_total += h["valuation"]
                    details.append((f"α{token}", h["amount"], h["valuation"]))

        total += alpha_total

        items.append({"label": "────────", "value": "────────", "color": "#666666"})
        items.append({
            "label": "持仓总值",
            "value": format_value(total),
            "color": "#2196F3",
        })
        for token, _amount, value in details:
            items.append({
                "label": token,
                "value": format_value(value),
                "color": "#9E9E9E",
            })

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
