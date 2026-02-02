"""Tests for unity_cli/api/selection.py - Selection API"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from unity_cli.api.selection import SelectionAPI


@pytest.fixture
def mock_conn() -> MagicMock:
    """Create a mock relay connection."""
    return MagicMock()


@pytest.fixture
def sut(mock_conn: MagicMock) -> SelectionAPI:
    """Create a SelectionAPI instance with mock connection."""
    return SelectionAPI(mock_conn)


class TestGet:
    """get() メソッドのテスト"""

    def test_get_sends_selection_command(self, sut: SelectionAPI, mock_conn: MagicMock) -> None:
        """Send 'selection' as the command name."""
        mock_conn.send_request.return_value = {}

        sut.get()

        assert mock_conn.send_request.call_args[0][0] == "selection"

    def test_get_sends_get_action(self, sut: SelectionAPI, mock_conn: MagicMock) -> None:
        """Send action='get' to retrieve current selection."""
        mock_conn.send_request.return_value = {}

        sut.get()

        params = mock_conn.send_request.call_args[0][1]
        assert params == {"action": "get"}

    def test_get_returns_response(self, sut: SelectionAPI, mock_conn: MagicMock) -> None:
        """Return the selection response including objects and GUIDs."""
        expected = {
            "count": 1,
            "activeObject": {"name": "Main Camera", "type": "Camera", "instanceID": 100},
            "gameObjects": [{"name": "Main Camera"}],
            "assetGUIDs": [],
        }
        mock_conn.send_request.return_value = expected

        result = sut.get()

        assert result == expected
