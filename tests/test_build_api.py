"""Tests for unity_cli/api/build.py - Build API"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from unity_cli.api.build import BuildAPI


@pytest.fixture
def mock_conn() -> MagicMock:
    return MagicMock()


@pytest.fixture
def sut(mock_conn: MagicMock) -> BuildAPI:
    return BuildAPI(mock_conn)


class TestBuildAPISettings:
    def test_settings_sends_build_command(self, sut: BuildAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {"activeBuildTarget": "StandaloneWindows64"}

        sut.settings()

        call_args = mock_conn.send_request.call_args
        assert call_args[0][0] == "build"
        assert call_args[0][1]["action"] == "settings"


class TestBuildAPIBuild:
    def test_build_sends_default_params(self, sut: BuildAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {"success": True}

        sut.build()

        call_args = mock_conn.send_request.call_args
        assert call_args[0][0] == "build"
        assert call_args[0][1]["action"] == "build"

    def test_build_with_target_includes_target(self, sut: BuildAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {"success": True}

        sut.build(target="Android")

        params = mock_conn.send_request.call_args[0][1]
        assert params["target"] == "Android"

    def test_build_with_output_path_includes_output_path(self, sut: BuildAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {"success": True}

        sut.build(output_path="./Builds/Win")

        params = mock_conn.send_request.call_args[0][1]
        assert params["outputPath"] == "./Builds/Win"

    def test_build_with_scenes_includes_scenes(self, sut: BuildAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {"success": True}

        sut.build(scenes=["a.unity", "b.unity"])

        params = mock_conn.send_request.call_args[0][1]
        assert params["scenes"] == ["a.unity", "b.unity"]

    def test_build_passes_timeout_ms(self, sut: BuildAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {"success": True}

        sut.build()

        kwargs = mock_conn.send_request.call_args[1]
        assert kwargs["timeout_ms"] == 600_000


class TestBuildAPIScenes:
    def test_scenes_sends_build_command(self, sut: BuildAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {"scenes": []}

        sut.scenes()

        call_args = mock_conn.send_request.call_args
        assert call_args[0][0] == "build"
        assert call_args[0][1]["action"] == "scenes"
