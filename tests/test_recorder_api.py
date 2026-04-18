"""Tests for unity_cli/api/recorder.py - Recorder API"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from unity_cli.api.recorder import RecorderAPI


@pytest.fixture
def mock_conn() -> MagicMock:
    """Create a mock relay connection."""
    return MagicMock()


@pytest.fixture
def sut(mock_conn: MagicMock) -> RecorderAPI:
    """Create a RecorderAPI instance with mock connection."""
    return RecorderAPI(mock_conn)


class TestStart:
    """start() メソッドのテスト"""

    def test_sends_recorder_command(self, sut: RecorderAPI, mock_conn: MagicMock) -> None:
        """Send 'recorder' as the command name."""
        mock_conn.send_request.return_value = {}

        sut.start()

        assert mock_conn.send_request.call_args[0][0] == "recorder"

    def test_sends_start_action(self, sut: RecorderAPI, mock_conn: MagicMock) -> None:
        """Send action='start' をパラメータに含む。"""
        mock_conn.send_request.return_value = {}

        sut.start()

        params = mock_conn.send_request.call_args[0][1]
        assert params["action"] == "start"

    def test_default_params(self, sut: RecorderAPI, mock_conn: MagicMock) -> None:
        """デフォルトパラメータの確認。"""
        mock_conn.send_request.return_value = {}

        sut.start()

        params = mock_conn.send_request.call_args[0][1]
        assert params["fps"] == 30
        assert params["format"] == "jpg"
        assert params["quality"] == 75
        assert params["width"] == 1920
        assert params["height"] == 1080

    def test_custom_params(self, sut: RecorderAPI, mock_conn: MagicMock) -> None:
        """カスタムパラメータが正しく送信される。"""
        mock_conn.send_request.return_value = {}

        sut.start(fps=60, format="png", quality=100, width=3840, height=2160)

        params = mock_conn.send_request.call_args[0][1]
        assert params["fps"] == 60
        assert params["format"] == "png"
        assert params["quality"] == 100
        assert params["width"] == 3840
        assert params["height"] == 2160

    def test_camera_param_included_when_set(self, sut: RecorderAPI, mock_conn: MagicMock) -> None:
        """camera 指定時にパラメータに含まれる。"""
        mock_conn.send_request.return_value = {}

        sut.start(camera="OverviewCam")

        params = mock_conn.send_request.call_args[0][1]
        assert params["camera"] == "OverviewCam"

    def test_camera_param_excluded_when_none(self, sut: RecorderAPI, mock_conn: MagicMock) -> None:
        """camera=None の場合パラメータに含まれない。"""
        mock_conn.send_request.return_value = {}

        sut.start()

        params = mock_conn.send_request.call_args[0][1]
        assert "camera" not in params

    def test_output_dir_included_when_set(self, sut: RecorderAPI, mock_conn: MagicMock) -> None:
        """output_dir 指定時にパラメータに含まれる。"""
        mock_conn.send_request.return_value = {}

        sut.start(output_dir="/tmp/frames")

        params = mock_conn.send_request.call_args[0][1]
        assert params["outputDir"] == "/tmp/frames"

    def test_output_dir_excluded_when_none(self, sut: RecorderAPI, mock_conn: MagicMock) -> None:
        """output_dir=None の場合パラメータに含まれない。"""
        mock_conn.send_request.return_value = {}

        sut.start()

        params = mock_conn.send_request.call_args[0][1]
        assert "outputDir" not in params

    def test_returns_response(self, sut: RecorderAPI, mock_conn: MagicMock) -> None:
        """send_request の戻り値をそのまま返す。"""
        expected = {"message": "Recording started", "outputDir": "/tmp/frames"}
        mock_conn.send_request.return_value = expected

        result = sut.start()

        assert result == expected


class TestStop:
    """stop() メソッドのテスト"""

    def test_sends_recorder_command(self, sut: RecorderAPI, mock_conn: MagicMock) -> None:
        """Send 'recorder' as the command name."""
        mock_conn.send_request.return_value = {}

        sut.stop()

        assert mock_conn.send_request.call_args[0][0] == "recorder"

    def test_sends_stop_action(self, sut: RecorderAPI, mock_conn: MagicMock) -> None:
        """Send action='stop'。"""
        mock_conn.send_request.return_value = {}

        sut.stop()

        params = mock_conn.send_request.call_args[0][1]
        assert params == {"action": "stop"}

    def test_returns_response(self, sut: RecorderAPI, mock_conn: MagicMock) -> None:
        """結果（frameCount, elapsed 等）を返す。"""
        expected = {"frameCount": 300, "elapsed": 10.0, "fps": 30.0, "outputDir": "/tmp/frames"}
        mock_conn.send_request.return_value = expected

        result = sut.stop()

        assert result == expected


class TestStatus:
    """status() メソッドのテスト"""

    def test_sends_recorder_command(self, sut: RecorderAPI, mock_conn: MagicMock) -> None:
        """Send 'recorder' as the command name."""
        mock_conn.send_request.return_value = {}

        sut.status()

        assert mock_conn.send_request.call_args[0][0] == "recorder"

    def test_sends_status_action(self, sut: RecorderAPI, mock_conn: MagicMock) -> None:
        """Send action='status'。"""
        mock_conn.send_request.return_value = {}

        sut.status()

        params = mock_conn.send_request.call_args[0][1]
        assert params == {"action": "status"}

    def test_returns_response(self, sut: RecorderAPI, mock_conn: MagicMock) -> None:
        """録画状態を返す。"""
        expected = {"recording": True, "frameCount": 150, "elapsed": 5.0, "fps": 30.0, "pendingWrites": 2}
        mock_conn.send_request.return_value = expected

        result = sut.status()

        assert result == expected
