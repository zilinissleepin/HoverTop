# python/tests/test_app_manager.py
from pathlib import Path
from unittest.mock import patch

from hovertop.app_manager import find_app, launch_app


def test_find_app_in_project_dir(tmp_path: Path):
    app_path = tmp_path / "HoverTop.app"
    app_path.mkdir()
    with patch("hovertop.app_manager._get_search_paths", return_value=[tmp_path]):
        result = find_app()
    assert result == app_path


def test_find_app_not_found(tmp_path: Path):
    with patch("hovertop.app_manager._get_search_paths", return_value=[tmp_path]):
        result = find_app()
    assert result is None


def test_launch_app_returns_process(tmp_path: Path):
    app_path = tmp_path / "HoverTop.app"
    app_path.mkdir()
    with patch("hovertop.app_manager.find_app", return_value=app_path):
        proc = launch_app(port=9527)
    assert proc is not None
    proc.terminate()


def test_launch_app_passes_port_and_offset(tmp_path: Path):
    """launch_app 必须把 --port 和 --offset-y 传给 Swift CLI。"""
    app_path = tmp_path / "HoverTop.app"
    app_path.mkdir()
    with patch("hovertop.app_manager.find_app", return_value=app_path), \
         patch("hovertop.app_manager.subprocess.Popen") as mock_popen:
        launch_app(port=12345, offset_y=240)

    cmd = mock_popen.call_args.args[0]
    assert "--port" in cmd
    assert "12345" in cmd
    assert "--offset-y" in cmd
    assert "240" in cmd
    # .app bundle 走 open -n (允许多实例)
    assert "-n" in cmd
