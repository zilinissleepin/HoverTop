# 股票行情悬浮窗 设计文档

日期: 2026-05-08
类型: 新增示例脚本

## 目标

新增一个 HoverTop 示例脚本，实时展示 A股、港股、美股 的当前价和涨跌幅，每 10 秒刷新。风格与已有的 `binance_dashboard.py` 对齐，作为“纯行情、无持仓”的轻量参考实现。

## 非目标

- 不做持仓/成本/盈亏计算
- 不判断交易时段，非交易时段直接显示最后成交价
- 不区分美股盘前盘后
- 不做走势图、K线、历史数据

## 用户配置

在 `python/.env` 增加三个独立的环境变量（任一可空，空市场不显示）：

```
CN_STOCKS=sh600519,sz000001
HK_STOCKS=00700,09988
US_STOCKS=AAPL,TSLA
```

- A股 使用新浪前缀 `sh` / `sz`
- 港股 使用 5 位数字代码（不足 5 位前面补 0）
- 美股 使用大写 ticker

可选：

```
REFRESH_INTERVAL=10   # 默认 10 秒，允许用户自定义
```

## 架构

新增单文件 `python/examples/stock_dashboard.py`，结构参考 `binance_dashboard.py`：

```
stock_dashboard.py
├── 配置读取 (load_dotenv + 三个 _parse_list)
├── 行情获取
│   ├── fetch_cn_quotes(codes)  → dict[code, Quote]
│   ├── fetch_hk_quotes(codes)  → dict[code, Quote]
│   └── fetch_us_quotes(codes)  → dict[code, Quote]
├── build_data()  组装悬浮窗数据
└── main()        循环调用 widget.update
```

其中 `Quote` 用一个简单的 `TypedDict`：

```python
class Quote(TypedDict):
    name: str         # 股票中文/英文名
    price: float      # 当前价
    change_pct: float # 涨跌幅 %
```

## 数据源

全部使用新浪财经统一端点：

```
GET https://hq.sinajs.cn/list=<逗号分隔的 code 列表>
Referer: https://finance.sina.com.cn
```

**必须带 Referer 头**，否则返回 403。

### A股

- 请求：`list=sh600519,sz000001`
- 返回示例：`var hq_str_sh600519="贵州茅台,1650.00,1630.00,1655.00,...";`
- 字段顺序（逗号分割）：`[0]名称 [1]今开 [2]昨收 [3]当前价 [4]最高 [5]最低 ...`
- 涨跌幅自算：`(current - prev_close) / prev_close * 100`

### 港股

- 请求：`list=hk00700,hk09988`
- 返回字段顺序：`[0]英文名 [1]中文名 [2]今开 [3]昨收 [4]最高 [5]最低 [6]当前价 ...`
- 涨跌幅自算同上

### 美股

- 请求：`list=gb_aapl,gb_tsla`（ticker 要小写加 `gb_` 前缀）
- 返回字段顺序：`[0]名称 [1]当前价 [2]涨跌幅 [3]日期 ... [26]昨收 ...`
- **涨跌幅** 字段直接可用，无需自算

### 编码

新浪返回是 GBK 编码（A股/港股有中文），需要 `response.content.decode("gbk")`。

## 解析失败处理

单支股票解析失败时，对应 key 不写入结果 dict；上层看到缺失就渲染成 `—`，不中断其他数据。整个市场请求失败（网络错误、超时）时记 stderr，本轮该市场全部显示 `—`。

沿用已有的 `log_err()` 风格：

```python
def log_err(where: str, exc: BaseException) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {where}: {type(exc).__name__}: {exc}", file=sys.stderr)
    if os.environ.get("DEBUG"):
        traceback.print_exc(file=sys.stderr)
```

请求超时固定 10s，不做重试（下一轮 10s 自然重来）。

## 悬浮窗布局

```
股票行情           ← title
HH:MM:SS           ← subtitle
──────────
A股                ← 分段表头 (橙色 #FF9800, 无数值)
  贵州茅台  1650.00  +1.23%
  平安银行    12.45  -0.80%
港股
  腾讯控股   380.00  +0.53%
  阿里巴巴    82.10  -1.10%
美股
  AAPL      175.00  +0.86%
  TSLA      245.00  -2.30%
每 10 秒刷新 | Ctrl+C 退出   ← footer
```

DisplayItem 映射（每行 2 列 cells：价格、涨跌幅）：

- 分段表头：`label=市场名, value="", color="#FF9800", cells=["", ""]`
- 股票行：`label=股票名, value="", color=涨跌色, cells=[price_str, change_str]`

### 排序

每个市场段内按 `change_pct` 降序（涨幅最大的在上）。解析失败的股票排最后。

### 空市场处理

对应 `_STOCKS` 环境变量为空时，该市场段（含表头）完全不渲染。

### 颜色

用户选择的方案是"涨绿跌红"（与现有 `binance_dashboard.py` 一致）：

- 涨 (`change_pct >= 0`)：绿 `#4CAF50`
- 跌 (`change_pct < 0`)：红 `#F44336`
- 解析失败/数据缺失：白 `#FFFFFF`

## 数值格式

沿用 `binance_dashboard` 的 `format_number` 思路：

- 当前价：价格 >= 1 保留 2 位小数（带千分位），< 1 保留 4 位有效数字
- 涨跌幅：`f"{change:+.2f}%"`，始终带 `+` / `-` 号

## 代码约束

- 严格类型标注（mypy-friendly）：所有函数签名、返回 dict 都用 `TypedDict` 或显式 `dict[str, ...]`
- 依赖仅用 `requests` + `python-dotenv`（均已在 `pyproject.toml`）
- 不新增第三方依赖
- 不创建新的包模块，单文件即可

## 测试

在 `python/tests/` 新增 `test_stock_dashboard.py`：

1. 解析函数的纯函数测试：mock `requests.get` 的 `.content`（GBK 编码的样例响应），验证 `fetch_cn_quotes` / `fetch_hk_quotes` / `fetch_us_quotes` 的字段提取和涨跌幅计算。
2. 样例必须包含：
   - 正常 A股响应（含中文名）
   - 美股响应（验证涨跌幅字段直接取用）
   - 异常响应：字段数不足、空字符串（验证不抛异常、不写入结果）
3. 涨跌幅排序的单测：`build_data` 中的排序逻辑可抽成纯函数 `_sort_market_rows`，单测覆盖。

不测试 `build_data` 的完整流程（涉及 Widget IO），不测试 `main` 循环。

## 手动验收

1. 只配 `CN_STOCKS=sh600519,sz000001` 启动，应显示 A股 两行，无港股/美股段
2. 配齐三市场启动，应显示三个分段
3. 故意配一个无效 code（如 `sh999999`），应显示 `—`，其他股票不受影响
4. 断网启动，应显示 title+subtitle+分段头，每行 `—`，不崩溃
5. `DEBUG=1` 启动，遇错应看到完整 traceback

## 不在本次范围

- 国债/期货/加密对标的股票化展示
- 自选股分组
- 持仓价值总和（币安仪表盘已覆盖这个场景）
- 收盘时间判断与样式变灰
