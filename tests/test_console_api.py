"""Tests for unity_cli/api/console.py - Console API"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from unity_cli.api.console import ConsoleAPI


@pytest.fixture
def mock_conn() -> MagicMock:
    return MagicMock()


@pytest.fixture
def sut(mock_conn: MagicMock) -> ConsoleAPI:
    return ConsoleAPI(mock_conn)


class TestGet:
    """get() メソッドのテスト"""

    def test_get_sends_console_command(self, sut: ConsoleAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {}

        sut.get()

        assert mock_conn.send_request.call_args[0][0] == "console"

    def test_get_sends_read_action_with_defaults(self, sut: ConsoleAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {}

        sut.get()

        params = mock_conn.send_request.call_args[0][1]
        assert params["action"] == "read"
        assert params["format"] == "detailed"
        assert params["include_stacktrace"] is False

    def test_get_with_types(self, sut: ConsoleAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {}

        sut.get(types=["error", "warning"])

        params = mock_conn.send_request.call_args[0][1]
        assert params["types"] == ["error", "warning"]

    def test_get_without_types_excludes_types_key(self, sut: ConsoleAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {}

        sut.get()

        params = mock_conn.send_request.call_args[0][1]
        assert "types" not in params

    def test_get_with_count(self, sut: ConsoleAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {}

        sut.get(count=10)

        params = mock_conn.send_request.call_args[0][1]
        assert params["count"] == 10

    def test_get_without_count_excludes_count_key(self, sut: ConsoleAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {}

        sut.get()

        params = mock_conn.send_request.call_args[0][1]
        assert "count" not in params

    def test_get_with_filter_text(self, sut: ConsoleAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {}

        sut.get(filter_text="NullReference")

        params = mock_conn.send_request.call_args[0][1]
        assert params["search"] == "NullReference"

    def test_get_with_stacktrace(self, sut: ConsoleAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {}

        sut.get(include_stacktrace=True)

        params = mock_conn.send_request.call_args[0][1]
        assert params["include_stacktrace"] is True

    def test_get_with_simple_format(self, sut: ConsoleAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {}

        sut.get(format="simple")

        params = mock_conn.send_request.call_args[0][1]
        assert params["format"] == "simple"


class TestClear:
    """clear() メソッドのテスト"""

    def test_clear_sends_console_command(self, sut: ConsoleAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {}

        sut.clear()

        assert mock_conn.send_request.call_args[0][0] == "console"

    def test_clear_sends_clear_action(self, sut: ConsoleAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {}

        sut.clear()

        params = mock_conn.send_request.call_args[0][1]
        assert params == {"action": "clear"}
