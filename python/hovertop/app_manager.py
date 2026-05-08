from __future__ import annotations

import subprocess
from pathlib import Path


def _get_search_paths() -> list[Path]:
    """返回按优先级排列的 app 搜索路径"""
    paths: list[Path] = []
    # 1. 项目目录内的构建产物
    project_root = Path(__file__).parent.parent.parent
    paths.append(project_root / "swift" / ".build" / "release")
    paths.append(project_root / "swift" / ".build" / "debug")
    # 2. 用户 home 目录
    paths.append(Path.home() / ".hovertop")
    return paths


def find_app() -> Path | None:
    """查找 HoverTop 可执行文件或 app bundle"""
    for search_path in _get_search_paths():
        app = search_path / "HoverTop"
        if app.exists() and app.is_file():
            return app
        # 也检查 .app bundle（macOS 应用目录）
        app_bundle = search_path / "HoverTop.app"
        if app_bundle.exists() and app_bundle.is_dir():
            return app_bundle
    return None


def launch_app(port: int = 9527, offset_y: float = 0) -> subprocess.Popen[bytes] | None:
    """启动 HoverTop app, 传递 WebSocket 端口和窗口 Y 偏移

    - port: Swift app 连接的 WebSocket 端口
    - offset_y: 窗口相对于屏幕右上角默认位置向下的像素偏移, 用于多窗口错开
    """
    app_path = find_app()
    if app_path is None:
        return None
    cli_args = ["--port", str(port), "--offset-y", str(offset_y)]
    # macOS .app bundle 使用 open 命令启动; -n 允许启动多个实例
    if app_path.is_dir() and app_path.suffix == ".app":
        proc = subprocess.Popen(
            ["open", "-n", "-a", str(app_path), "--args", *cli_args],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        proc = subprocess.Popen(
            [str(app_path), *cli_args],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    return proc
