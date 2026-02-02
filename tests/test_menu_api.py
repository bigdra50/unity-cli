"""Tests for unity_cli/api/menu.py - Menu API"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from unity_cli.api.menu import MenuAPI


@pytest.fixture
def mock_conn() -> MagicMock:
    """Create a mock relay connection."""
    return MagicMock()


@pytest.fixture
def sut(mock_conn: MagicMock) -> MenuAPI:
    """Create a MenuAPI instance with mock connection."""
    return MenuAPI(mock_conn)


class TestExecute:
    """execute() メソッドのテスト"""

    def test_execute_sends_menu_command(self, sut: MenuAPI, mock_conn: MagicMock) -> None:
        """Send 'menu' as the command name."""
        mock_conn.send_request.return_value = {}

        sut.execute("Edit/Play")

        assert mock_conn.send_request.call_args[0][0] == "menu"

    def test_execute_sends_path(self, sut: MenuAPI, mock_conn: MagicMock) -> None:
        """Send action='execute' with the menu path."""
        mock_conn.send_request.return_value = {}

        sut.execute("Window/General/Console")

        params = mock_conn.send_request.call_args[0][1]
        assert params == {"action": "execute", "path": "Window/General/Console"}

    def test_execute_returns_response(self, sut: MenuAPI, mock_conn: MagicMock) -> None:
        """Return the execution result response."""
        expected = {"success": True, "path": "Edit/Play", "message": "Executed"}
        mock_conn.send_request.return_value = expected

        result = sut.execute("Edit/Play")

        assert result == expected


class TestList:
    """list() メソッドのテスト"""

    def test_list_sends_list_action(self, sut: MenuAPI, mock_conn: MagicMock) -> None:
        """Send action='list' to retrieve menu items."""
        mock_conn.send_request.return_value = {}

        sut.list()

        params = mock_conn.send_request.call_args[0][1]
        assert params["action"] == "list"

    def test_list_default_limit(self, sut: MenuAPI, mock_conn: MagicMock) -> None:
        """Default limit is 100."""
        mock_conn.send_request.return_value = {}

        sut.list()

        params = mock_conn.send_request.call_args[0][1]
        assert params["limit"] == 100

    def test_list_with_custom_limit(self, sut: MenuAPI, mock_conn: MagicMock) -> None:
        """Send custom limit value."""
        mock_conn.send_request.return_value = {}

        sut.list(limit=50)

        params = mock_conn.send_request.call_args[0][1]
        assert params["limit"] == 50

    def test_list_with_filter(self, sut: MenuAPI, mock_conn: MagicMock) -> None:
        """Include filter key when filter_text is provided."""
        mock_conn.send_request.return_value = {}

        sut.list(filter_text="Window")

        params = mock_conn.send_request.call_args[0][1]
        assert params["filter"] == "Window"

    def test_list_without_filter_excludes_filter_key(self, sut: MenuAPI, mock_conn: MagicMock) -> None:
        """Exclude filter key when filter_text is not provided."""
        mock_conn.send_request.return_value = {}

        sut.list()

        params = mock_conn.send_request.call_args[0][1]
        assert "filter" not in params


class TestContext:
    """context() メソッドのテスト"""

    def test_context_sends_context_action(self, sut: MenuAPI, mock_conn: MagicMock) -> None:
        """Send action='context' with the method name."""
        mock_conn.send_request.return_value = {}

        sut.context(method="Reset")

        params = mock_conn.send_request.call_args[0][1]
        assert params["action"] == "context"
        assert params["method"] == "Reset"

    def test_context_with_target(self, sut: MenuAPI, mock_conn: MagicMock) -> None:
        """Include target key when target is provided."""
        mock_conn.send_request.return_value = {}

        sut.context(method="Reset", target="Main Camera")

        params = mock_conn.send_request.call_args[0][1]
        assert params["target"] == "Main Camera"

    def test_context_without_target_excludes_target_key(self, sut: MenuAPI, mock_conn: MagicMock) -> None:
        """Exclude target key when target is not provided."""
        mock_conn.send_request.return_value = {}

        sut.context(method="Reset")

        params = mock_conn.send_request.call_args[0][1]
        assert "target" not in params
