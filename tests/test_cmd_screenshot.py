"""Tests for unity_cli/cli/commands/screenshot.py - Screenshot CLI Command

screenshot コマンドは Relay 経由で Unity Editor に接続するため、
UnityClient を mock に差し替えてテストする。
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from unity_cli.cli.app import app

runner = CliRunner()


def _make_mock_client(screenshot_return: dict | None = None) -> MagicMock:
    """screenshot API の戻り値を設定した mock client を生成。"""
    client = MagicMock()
    client.screenshot.capture.return_value = screenshot_return or {
        "message": "Screenshot captured",
        "path": "/tmp/screenshot.png",
        "source": "game",
    }
    client.screenshot.burst.return_value = screenshot_return or {
        "frameCount": 10,
        "outputDir": "/tmp/burst",
        "format": "jpg",
        "elapsed": 1.5,
        "fps": 6.67,
    }
    return client


def _invoke(args: list[str], client: MagicMock | None = None) -> object:
    """UnityClient を mock して CliRunner.invoke を実行。"""
    mock_client = client or _make_mock_client()
    with patch("unity_cli.client.UnityClient", return_value=mock_client):
        return runner.invoke(app, args)


class TestScreenshotCapture:
    """screenshot (capture mode) のテスト"""

    def test_default_capture(self) -> None:
        """デフォルトのキャプチャが成功する。"""
        result = _invoke(["screenshot"])
        assert result.exit_code == 0

    def test_capture_calls_api(self) -> None:
        """API が正しく呼ばれる。"""
        client = _make_mock_client()
        _invoke(["screenshot", "-s", "game"], client)
        client.screenshot.capture.assert_called_once()

    def test_capture_with_source_scene(self) -> None:
        """--source scene が API に渡される。"""
        client = _make_mock_client()
        _invoke(["screenshot", "-s", "scene"], client)
        call_kwargs = client.screenshot.capture.call_args
        assert call_kwargs.kwargs.get("source") == "scene" or (call_kwargs.args and call_kwargs.args[0] == "scene")

    def test_capture_json_output(self) -> None:
        """--json でJSON形式の出力。"""
        result = _invoke(["screenshot", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "path" in data

    def test_capture_with_path_option(self) -> None:
        """--path オプションが API に渡される。"""
        client = _make_mock_client()
        _invoke(["screenshot", "-p", "/tmp/out.png"], client)
        client.screenshot.capture.assert_called_once()
        kwargs = client.screenshot.capture.call_args[1]
        assert kwargs.get("path") == "/tmp/out.png"

    def test_invalid_source(self) -> None:
        """不正な source でエラー終了。"""
        result = _invoke(["screenshot", "-s", "invalid_source"])
        assert result.exit_code != 0

    def test_invalid_format(self) -> None:
        """不正な format でエラー終了。"""
        result = _invoke(["screenshot", "-f", "bmp"])
        assert result.exit_code != 0


class TestScreenshotBurst:
    """screenshot --burst のテスト"""

    def test_burst_mode(self) -> None:
        """--burst でバーストキャプチャが成功する。"""
        result = _invoke(["screenshot", "--burst"])
        assert result.exit_code == 0

    def test_burst_calls_burst_api(self) -> None:
        """--burst で burst API が呼ばれる。"""
        client = _make_mock_client()
        _invoke(["screenshot", "--burst"], client)
        client.screenshot.burst.assert_called_once()
        client.screenshot.capture.assert_not_called()

    def test_burst_json_output(self) -> None:
        """--burst --json でJSON形式の出力。"""
        result = _invoke(["screenshot", "--burst", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "frameCount" in data

    def test_burst_with_count(self) -> None:
        """--count オプションが API に渡される。"""
        client = _make_mock_client()
        _invoke(["screenshot", "--burst", "-n", "50"], client)
        kwargs = client.screenshot.burst.call_args[1]
        assert kwargs.get("count") == 50

    def test_burst_invalid_format(self) -> None:
        """--burst + 不正な format でエラー終了。"""
        result = _invoke(["screenshot", "--burst", "-f", "gif"])
        assert result.exit_code != 0
