# HoverTop

macOS 桌面悬浮窗，通过 Python 脚本控制内容和样式。

## 快速开始

### 1. 构建 Swift 应用

```bash
./build.sh
```

### 2. 安装 Python SDK

```bash
cd python && uv sync
```

### 3. 运行示例

```bash
uv run python examples/system_monitor.py
uv run python examples/binance_dashboard.py
```

## Python API

```python
from hovertop import Widget

# 创建悬浮窗
widget = Widget("我的悬浮窗")

# 更新内容
widget.update(
    title="标题",
    subtitle="副标题",
    items=[
        {"label": "项目", "value": "值", "color": "#4CAF50"},
    ],
    footer="底部文字",
)

# 使用上下文管理器
with Widget("监控") as w:
    w.update(items=[{"label": "CPU", "value": "23%"}])
```

## 数据格式

| 字段 | 类型 | 说明 |
|------|------|------|
| title | string | 标题 |
| subtitle | string | 副标题 |
| items | list | 数据项 |
| items[].label | string | 名称 |
| items[].value | string | 值 |
| items[].color | string | 颜色 (十六进制) |
| footer | string | 底部文字 |
