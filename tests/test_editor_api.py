"""Tests for unity_cli/api/editor.py - Editor API"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from unity_cli.api.editor import EditorAPI


@pytest.fixture
def mock_conn() -> MagicMock:
    """Create a mock relay connection."""
    return MagicMock()


@pytest.fixture
def sut(mock_conn: MagicMock) -> EditorAPI:
    """Create an EditorAPI instance with mock connection."""
    return EditorAPI(mock_conn)


class TestPlay:
    """play() メソッドのテスト"""

    def test_play_sends_playmode_command(self, sut: EditorAPI, mock_conn: MagicMock) -> None:
        """Send 'playmode' as the command name."""
        mock_conn.send_request.return_value = {}

        sut.play()

        assert mock_conn.send_request.call_args[0][0] == "playmode"

    def test_play_sends_enter_action(self, sut: EditorAPI, mock_conn: MagicMock) -> None:
        """Send action='enter' to enter play mode."""
        mock_conn.send_request.return_value = {}

        sut.play()

        params = mock_conn.send_request.call_args[0][1]
        assert params == {"action": "enter"}

    def test_play_returns_response(self, sut: EditorAPI, mock_conn: MagicMock) -> None:
        """Return the response from send_request."""
        expected = {"isPlaying": True}
        mock_conn.send_request.return_value = expected

        result = sut.play()

        assert result == expected


class TestPause:
    """pause() メソッドのテスト"""

    def test_pause_sends_pause_action(self, sut: EditorAPI, mock_conn: MagicMock) -> None:
        """Send action='pause' to pause the game."""
        mock_conn.send_request.return_value = {}

        sut.pause()

        params = mock_conn.send_request.call_args[0][1]
        assert params == {"action": "pause"}


class TestUnpause:
    """unpause() メソッドのテスト"""

    def test_unpause_sends_unpause_action(self, sut: EditorAPI, mock_conn: MagicMock) -> None:
        """Send action='unpause' to resume the game."""
        mock_conn.send_request.return_value = {}

        sut.unpause()

        params = mock_conn.send_request.call_args[0][1]
        assert params == {"action": "unpause"}


class TestStop:
    """stop() メソッドのテスト"""

    def test_stop_sends_exit_action(self, sut: EditorAPI, mock_conn: MagicMock) -> None:
        """Send action='exit' to exit play mode."""
        mock_conn.send_request.return_value = {}

        sut.stop()

        params = mock_conn.send_request.call_args[0][1]
        assert params == {"action": "exit"}


class TestStep:
    """step() メソッドのテスト"""

    def test_step_sends_step_action(self, sut: EditorAPI, mock_conn: MagicMock) -> None:
        """Send action='step' to advance one frame."""
        mock_conn.send_request.return_value = {}

        sut.step()

        params = mock_conn.send_request.call_args[0][1]
        assert params == {"action": "step"}


class TestGetState:
    """get_state() メソッドのテスト"""

    def test_get_state_sends_state_action(self, sut: EditorAPI, mock_conn: MagicMock) -> None:
        """Send action='state' to retrieve editor state."""
        mock_conn.send_request.return_value = {}

        sut.get_state()

        params = mock_conn.send_request.call_args[0][1]
        assert params == {"action": "state"}

    def test_get_state_returns_response(self, sut: EditorAPI, mock_conn: MagicMock) -> None:
        """Return the editor state response."""
        expected = {"isPlaying": False, "isPaused": False}
        mock_conn.send_request.return_value = expected

        result = sut.get_state()

        assert result == expected


class TestGetTags:
    """get_tags() メソッドのテスト"""

    def test_get_tags_sends_get_tags_command(self, sut: EditorAPI, mock_conn: MagicMock) -> None:
        """Send 'get_tags' as the command name."""
        mock_conn.send_request.return_value = {}

        sut.get_tags()

        assert mock_conn.send_request.call_args[0][0] == "get_tags"

    def test_get_tags_sends_empty_params(self, sut: EditorAPI, mock_conn: MagicMock) -> None:
        """Send empty params dict."""
        mock_conn.send_request.return_value = {}

        sut.get_tags()

        params = mock_conn.send_request.call_args[0][1]
        assert params == {}


class TestGetLayers:
    """get_layers() メソッドのテスト"""

    def test_get_layers_sends_get_layers_command(self, sut: EditorAPI, mock_conn: MagicMock) -> None:
        """Send 'get_layers' as the command name."""
        mock_conn.send_request.return_value = {}

        sut.get_layers()

        assert mock_conn.send_request.call_args[0][0] == "get_layers"

    def test_get_layers_sends_empty_params(self, sut: EditorAPI, mock_conn: MagicMock) -> None:
        """Send empty params dict."""
        mock_conn.send_request.return_value = {}

        sut.get_layers()

        params = mock_conn.send_request.call_args[0][1]
        assert params == {}


class TestRefresh:
    """refresh() メソッドのテスト"""

    def test_refresh_sends_refresh_command(self, sut: EditorAPI, mock_conn: MagicMock) -> None:
        """Send 'refresh' as the command name."""
        mock_conn.send_request.return_value = {}

        sut.refresh()

        assert mock_conn.send_request.call_args[0][0] == "refresh"

    def test_refresh_sends_empty_params(self, sut: EditorAPI, mock_conn: MagicMock) -> None:
        """Send empty params dict."""
        mock_conn.send_request.return_value = {}

        sut.refresh()

        params = mock_conn.send_request.call_args[0][1]
        assert params == {}
