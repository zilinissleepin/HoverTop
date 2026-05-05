"""系统监控悬浮窗示例 - 每 2 秒刷新 CPU 和内存使用率"""
import time
import psutil
from hovertop import Widget


def get_system_info():
    cpu = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    return {
        "title": "系统监控",
        "subtitle": time.strftime("%H:%M:%S"),
        "items": [
            {
                "label": "CPU",
                "value": f"{cpu:.1f}%",
                "color": "#4CAF50" if cpu < 50 else "#FF9800" if cpu < 80 else "#F44336",
            },
            {
                "label": "内存",
                "value": f"{mem.used / (1024**3):.1f}GB / {mem.total / (1024**3):.0f}GB",
                "color": "#4CAF50" if mem.percent < 50 else "#FF9800" if mem.percent < 80 else "#F44336",
            },
        ],
        "footer": "每 2 秒刷新 | Ctrl+C 退出",
    }


def main():
    with Widget("系统监控") as widget:
        print("悬浮窗已启动，按 Ctrl+C 退出...")
        while True:
            widget.update(**get_system_info())
            time.sleep(2)


if __name__ == "__main__":
    main()
