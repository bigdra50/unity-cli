"""Tests for unity_cli/api/profiler.py - Profiler API"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from unity_cli.api.profiler import ProfilerAPI


@pytest.fixture
def mock_conn() -> MagicMock:
    return MagicMock()


@pytest.fixture
def sut(mock_conn: MagicMock) -> ProfilerAPI:
    return ProfilerAPI(mock_conn)


class TestProfilerAPIStatus:
    def test_status_sends_profiler_command(self, sut: ProfilerAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {"recording": False}

        sut.status()

        call_args = mock_conn.send_request.call_args
        assert call_args[0][0] == "profiler"
        assert call_args[0][1]["action"] == "status"


class TestProfilerAPIStart:
    def test_start_sends_start_action(self, sut: ProfilerAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {"recording": True}

        sut.start()

        call_args = mock_conn.send_request.call_args
        assert call_args[0][0] == "profiler"
        assert call_args[0][1]["action"] == "start"


class TestProfilerAPIStop:
    def test_stop_sends_stop_action(self, sut: ProfilerAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {"recording": False}

        sut.stop()

        call_args = mock_conn.send_request.call_args
        assert call_args[0][0] == "profiler"
        assert call_args[0][1]["action"] == "stop"


class TestProfilerAPISnapshot:
    def test_snapshot_sends_snapshot_action(self, sut: ProfilerAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {"frameIndex": 100}

        sut.snapshot()

        call_args = mock_conn.send_request.call_args
        assert call_args[0][0] == "profiler"
        assert call_args[0][1]["action"] == "snapshot"


class TestProfilerAPIFrames:
    def test_frames_sends_default_count(self, sut: ProfilerAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {"frames": []}

        sut.frames()

        call_args = mock_conn.send_request.call_args
        assert call_args[0][0] == "profiler"
        params = call_args[0][1]
        assert params["action"] == "frames"
        assert params["count"] == 10

    def test_frames_with_custom_count(self, sut: ProfilerAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {"frames": []}

        sut.frames(count=30)

        params = mock_conn.send_request.call_args[0][1]
        assert params["count"] == 30
