"""Tests for unity_cli/api/tests.py - Test API"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from unity_cli.api.tests import TestAPI


@pytest.fixture
def mock_conn() -> MagicMock:
    return MagicMock()


@pytest.fixture
def sut(mock_conn: MagicMock) -> TestAPI:
    return TestAPI(mock_conn)


class TestRun:
    """run() メソッドのテスト"""

    def test_run_sends_tests_command(self, sut: TestAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {}

        sut.run()

        assert mock_conn.send_request.call_args[0][0] == "tests"

    def test_run_sends_run_action(self, sut: TestAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {}

        sut.run()

        params = mock_conn.send_request.call_args[0][1]
        assert params["action"] == "run"

    def test_run_default_mode_is_edit(self, sut: TestAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {}

        sut.run()

        params = mock_conn.send_request.call_args[0][1]
        assert params["mode"] == "edit"

    def test_run_with_play_mode(self, sut: TestAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {}

        sut.run(mode="play")

        params = mock_conn.send_request.call_args[0][1]
        assert params["mode"] == "play"

    def test_run_with_test_names(self, sut: TestAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {}

        sut.run(test_names=["MyTests.TestA", "MyTests.TestB"])

        params = mock_conn.send_request.call_args[0][1]
        assert params["testNames"] == ["MyTests.TestA", "MyTests.TestB"]

    def test_run_with_categories(self, sut: TestAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {}

        sut.run(categories=["Unit", "Integration"])

        params = mock_conn.send_request.call_args[0][1]
        assert params["categories"] == ["Unit", "Integration"]

    def test_run_with_assemblies(self, sut: TestAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {}

        sut.run(assemblies=["Tests.EditMode"])

        params = mock_conn.send_request.call_args[0][1]
        assert params["assemblies"] == ["Tests.EditMode"]

    def test_run_with_group_pattern(self, sut: TestAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {}

        sut.run(group_pattern=".*Integration.*")

        params = mock_conn.send_request.call_args[0][1]
        assert params["groupPattern"] == ".*Integration.*"

    def test_run_without_optional_params_excludes_keys(self, sut: TestAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {}

        sut.run()

        params = mock_conn.send_request.call_args[0][1]
        assert params == {"action": "run", "mode": "edit"}


class TestList:
    """list() メソッドのテスト"""

    def test_list_sends_list_action(self, sut: TestAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {}

        sut.list()

        params = mock_conn.send_request.call_args[0][1]
        assert params["action"] == "list"

    def test_list_default_mode_is_edit(self, sut: TestAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {}

        sut.list()

        params = mock_conn.send_request.call_args[0][1]
        assert params == {"action": "list", "mode": "edit"}

    def test_list_with_play_mode(self, sut: TestAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {}

        sut.list(mode="play")

        params = mock_conn.send_request.call_args[0][1]
        assert params["mode"] == "play"


class TestStatus:
    """status() メソッドのテスト"""

    def test_status_sends_status_action(self, sut: TestAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {}

        sut.status()

        params = mock_conn.send_request.call_args[0][1]
        assert params == {"action": "status"}

    def test_status_returns_response(self, sut: TestAPI, mock_conn: MagicMock) -> None:
        expected = {"running": True, "passed": 5, "failed": 1}
        mock_conn.send_request.return_value = expected

        result = sut.status()

        assert result == expected
