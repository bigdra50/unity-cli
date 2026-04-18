"""Tests for unity_cli/api/screenshot.py - Screenshot API"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from unity_cli.api.screenshot import ScreenshotAPI


@pytest.fixture
def mock_conn() -> MagicMock:
    """Create a mock relay connection."""
    return MagicMock()


@pytest.fixture
def sut(mock_conn: MagicMock) -> ScreenshotAPI:
    """Create a ScreenshotAPI instance with mock connection."""
    return ScreenshotAPI(mock_conn)


class TestCapture:
    """capture() メソッドのテスト"""

    def test_sends_screenshot_command(self, sut: ScreenshotAPI, mock_conn: MagicMock) -> None:
        """Send 'screenshot' as the command name."""
        mock_conn.send_request.return_value = {}

        sut.capture()

        assert mock_conn.send_request.call_args[0][0] == "screenshot"

    def test_sends_capture_action(self, sut: ScreenshotAPI, mock_conn: MagicMock) -> None:
        """Send action='capture'。"""
        mock_conn.send_request.return_value = {}

        sut.capture()

        params = mock_conn.send_request.call_args[0][1]
        assert params["action"] == "capture"

    def test_default_params(self, sut: ScreenshotAPI, mock_conn: MagicMock) -> None:
        """デフォルトパラメータの確認。"""
        mock_conn.send_request.return_value = {}

        sut.capture()

        params = mock_conn.send_request.call_args[0][1]
        assert params["source"] == "game"
        assert params["superSize"] == 1

    @pytest.mark.parametrize(
        "source",
        ["game", "scene", "camera"],
    )
    def test_source_param(self, sut: ScreenshotAPI, mock_conn: MagicMock, source: str) -> None:
        """各 source が正しく送信される。"""
        mock_conn.send_request.return_value = {}

        sut.capture(source=source)  # type: ignore[arg-type]

        params = mock_conn.send_request.call_args[0][1]
        assert params["source"] == source

    def test_path_included_when_set(self, sut: ScreenshotAPI, mock_conn: MagicMock) -> None:
        """path 指定時にパラメータに含まれる。"""
        mock_conn.send_request.return_value = {}

        sut.capture(path="/tmp/shot.png")

        params = mock_conn.send_request.call_args[0][1]
        assert params["path"] == "/tmp/shot.png"

    def test_path_excluded_when_none(self, sut: ScreenshotAPI, mock_conn: MagicMock) -> None:
        """path=None の場合パラメータに含まれない。"""
        mock_conn.send_request.return_value = {}

        sut.capture()

        params = mock_conn.send_request.call_args[0][1]
        assert "path" not in params

    @pytest.mark.parametrize(
        ("param_name", "kwarg", "api_key"),
        [
            ("width", {"width": 3840}, "width"),
            ("height", {"height": 2160}, "height"),
            ("camera", {"camera": "MyCam"}, "camera"),
            ("format", {"format": "jpg"}, "format"),
            ("quality", {"quality": 95}, "quality"),
        ],
    )
    def test_optional_params_included_when_set(
        self,
        sut: ScreenshotAPI,
        mock_conn: MagicMock,
        param_name: str,
        kwarg: dict,
        api_key: str,
    ) -> None:
        """オプションパラメータが設定時にのみ含まれる。"""
        mock_conn.send_request.return_value = {}

        sut.capture(**kwarg)  # type: ignore[arg-type]

        params = mock_conn.send_request.call_args[0][1]
        assert api_key in params

    @pytest.mark.parametrize(
        "param_key",
        ["width", "height", "camera", "format", "quality"],
    )
    def test_optional_params_excluded_when_none(self, sut: ScreenshotAPI, mock_conn: MagicMock, param_key: str) -> None:
        """デフォルト None のオプションパラメータはリクエストに含まれない。"""
        mock_conn.send_request.return_value = {}

        sut.capture()

        params = mock_conn.send_request.call_args[0][1]
        assert param_key not in params

    def test_returns_response(self, sut: ScreenshotAPI, mock_conn: MagicMock) -> None:
        """send_request の戻り値をそのまま返す。"""
        expected = {"path": "/tmp/shot.png", "source": "game"}
        mock_conn.send_request.return_value = expected

        result = sut.capture()
        assert result == expected


class TestBurst:
    """burst() メソッドのテスト"""

    def test_sends_screenshot_command(self, sut: ScreenshotAPI, mock_conn: MagicMock) -> None:
        """Send 'screenshot' as the command name."""
        mock_conn.send_request.return_value = {}

        sut.burst()

        assert mock_conn.send_request.call_args[0][0] == "screenshot"

    def test_sends_burst_action(self, sut: ScreenshotAPI, mock_conn: MagicMock) -> None:
        """Send action='burst'。"""
        mock_conn.send_request.return_value = {}

        sut.burst()

        params = mock_conn.send_request.call_args[0][1]
        assert params["action"] == "burst"

    def test_default_params(self, sut: ScreenshotAPI, mock_conn: MagicMock) -> None:
        """デフォルトパラメータの確認。"""
        mock_conn.send_request.return_value = {}

        sut.burst()

        params = mock_conn.send_request.call_args[0][1]
        assert params["count"] == 10
        assert params["interval_ms"] == 0
        assert params["format"] == "jpg"
        assert params["quality"] == 75
        assert params["width"] == 1920
        assert params["height"] == 1080

    def test_custom_params(self, sut: ScreenshotAPI, mock_conn: MagicMock) -> None:
        """カスタムパラメータが正しく送信される。"""
        mock_conn.send_request.return_value = {}

        sut.burst(count=100, interval_ms=50, format="png", quality=100, width=3840, height=2160)

        params = mock_conn.send_request.call_args[0][1]
        assert params["count"] == 100
        assert params["interval_ms"] == 50
        assert params["format"] == "png"

    def test_camera_included_when_set(self, sut: ScreenshotAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {}

        sut.burst(camera="OverviewCam")

        params = mock_conn.send_request.call_args[0][1]
        assert params["camera"] == "OverviewCam"

    def test_camera_excluded_when_none(self, sut: ScreenshotAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {}

        sut.burst()

        params = mock_conn.send_request.call_args[0][1]
        assert "camera" not in params

    def test_output_dir_included_when_set(self, sut: ScreenshotAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {}

        sut.burst(output_dir="/tmp/burst")

        params = mock_conn.send_request.call_args[0][1]
        assert params["outputDir"] == "/tmp/burst"

    def test_output_dir_excluded_when_none(self, sut: ScreenshotAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {}

        sut.burst()

        params = mock_conn.send_request.call_args[0][1]
        assert "outputDir" not in params

    def test_timeout_ms_120000(self, sut: ScreenshotAPI, mock_conn: MagicMock) -> None:
        """burst は timeout_ms=120000 で送信。"""
        mock_conn.send_request.return_value = {}

        sut.burst()

        kwargs = mock_conn.send_request.call_args[1]
        assert kwargs["timeout_ms"] == 120000

    def test_returns_response(self, sut: ScreenshotAPI, mock_conn: MagicMock) -> None:
        expected = {"frameCount": 10, "outputDir": "/tmp/burst", "fps": 60.0}
        mock_conn.send_request.return_value = expected

        result = sut.burst()
        assert result == expected
