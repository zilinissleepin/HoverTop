# HoverTop 设计文档

## 概述

HoverTop 是一个 macOS 桌面悬浮窗工具，允许用户通过 Python 脚本定义悬浮窗的内容和样式。悬浮窗始终置顶显示，采用毛玻璃视觉效果，通过 WebSocket 实现 Python 与 Swift 原生应用之间的实时通信。

## 技术选型

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 悬浮窗实现 | Swift/SwiftUI 原生 | 性能最佳，macOS 原生体验 |
| 脚本控制 | Python SDK | 用户友好的脚本接口 |
| 通信方式 | WebSocket | 低延迟，低能耗，实时双向 |
| 视觉风格 | 毛玻璃 (Vibrancy) | 现代 macOS 风格 |
| 交互模式 | 纯展示 | 简单可靠，满足监控场景 |
| 内容格式 | 结构化数据 + 模板 | 易用性与灵活性平衡 |

## 架构

```
Python 脚本 (用户编写)
    │
    ▼
hovertop Python SDK
    │  WebSocket (ws://localhost:9527)
    ▼
HoverTop.app (Swift 原生)
    │
    ▼
macOS 悬浮窗 (毛玻璃, 置顶)
```

- **HoverTop.app**: 独立 Swift 进程，负责窗口渲染和置顶显示
- **hovertop Python SDK**: 提供简洁 API，内嵌 WebSocket 服务器
- **通信协议**: JSON over WebSocket，默认端口 9527

## 数据协议

### 消息格式

```json
{
  "title": "系统状态",
  "subtitle": "更新于 14:32",
  "items": [
    {"label": "CPU", "value": "23%", "color": "#4CAF50"},
    {"label": "内存", "value": "6.2GB / 16GB", "color": "#FF9800"},
    {"label": "磁盘", "value": "120GB 剩余", "color": "#2196F3"}
  ],
  "footer": "每 5 秒刷新"
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string | 否 | 窗口标题 |
| subtitle | string | 否 | 副标题，通常显示时间 |
| items | list | 否 | 数据项列表 |
| items[].label | string | 是 | 项目名称 |
| items[].value | string | 是 | 项目值 |
| items[].color | string | 否 | 值的颜色 (十六进制) |
| footer | string | 否 | 底部备注文字 |

## Python SDK 设计

### 使用方式

```python
import hovertop

# 方式 1: 手动管理生命周期
widget = hovertop.Widget("系统监控")
widget.update(
    title="系统状态",
    subtitle="实时监控",
    items=[
        {"label": "CPU", "value": "23%", "color": "#4CAF50"},
        {"label": "内存", "value": "6.2GB / 16GB"},
    ],
    footer="每 5 秒刷新"
)
# 程序结束时自动清理

# 方式 2: 上下文管理器
with hovertop.Widget("任务列表") as widget:
    widget.update(items=[...])
    # 退出 with 块时自动关闭悬浮窗
```

### API

- `hovertop.Widget(name, port=9527)` — 创建 Widget 实例，自动启动 HoverTop.app
- `widget.update(**kwargs)` — 更新悬浮窗内容
- `widget.close()` — 关闭悬浮窗和连接
- `widget.is_running` — 检查悬浮窗是否运行中

## 项目结构

```
HoverTop/
├── swift/                        # Swift macOS 应用
│   ├── Package.swift             # Swift Package Manager 配置
│   └── Sources/HoverTop/
│       ├── HoverTopApp.swift     # 应用入口
│       ├── FloatingWindow.swift  # 悬浮窗窗口管理
│       ├── ContentView.swift     # SwiftUI 渲染视图
│       ├── WebSocketClient.swift # WebSocket 客户端
│       └── Models.swift          # 数据模型
├── python/                       # Python SDK
│   ├── pyproject.toml
│   └── hovertop/
│       ├── __init__.py
│       ├── widget.py             # Widget 类
│       ├── server.py             # WebSocket 服务器
│       └── app_manager.py        # 查找/启动 Swift app
├── examples/                     # 示例脚本
│   ├── system_monitor.py
│   └── todo_list.py
└── README.md
```

## Swift 端技术细节

### 窗口管理 (FloatingWindow.swift)

- 使用 `NSWindow` 创建无边框窗口
- `window.level = .floating` 保证置顶
- `NSVisualEffectView` 实现毛玻璃背景
- 窗口可通过拖拽移动位置
- 默认尺寸: 280px 宽, 内容自适应高度

### 内容渲染 (ContentView.swift)

- SwiftUI 布局，动态行数
- 标题区: title (粗体) + subtitle (灰色小字)
- 数据区: label 左对齐, value 右对齐, 支持颜色
- 底部区: footer 灰色小字

### WebSocket 客户端 (WebSocketClient.swift)

- 使用 `URLSessionWebSocketTask` 连接 Python WebSocket 服务器
- 自动重连机制 (指数退避)
- JSON 解码为 `DisplayData` 模型

## Python 端技术细节

### WebSocket 服务器 (server.py)

- 基于 `websockets` 库
- 支持单客户端连接
- 异步非阻塞

### App 管理 (app_manager.py)

- 按优先级查找 HoverTop.app:
  1. 项目目录内的构建产物
  2. `~/.hovertop/HoverTop.app`
  3. 系统 PATH
- 使用 `subprocess` 启动 app
- 进程退出时自动清理

## 依赖

### Swift 端

- macOS 13+ (SwiftUI, URLSessionWebSocketTask)
- Xcode 15+ 或 Swift 5.9+

### Python 端

- Python 3.10+
- `websockets` >= 12.0
- 使用 `uv` 管理依赖

## 非功能需求

- 悬浮窗空闲时 CPU 占用接近 0
- WebSocket 空闲时无数据传输
- Python SDK 无额外线程开销 (asyncio)
- 窗口动画流畅 (60fps)
