"""Integration tests for EditorAPI commands."""

from __future__ import annotations

from unity_cli.api import EditorAPI


class TestState:
    def test_get_state_returns_valid_response(self, editor: EditorAPI) -> None:
        actual = editor.get_state()

        assert "isPlaying" in actual
        assert "isPaused" in actual

    def test_get_state_not_playing_by_default(self, editor: EditorAPI) -> None:
        actual = editor.get_state()

        assert actual["isPlaying"] is False


class TestRefresh:
    def test_refresh_succeeds(self, editor: EditorAPI) -> None:
        actual = editor.refresh()

        assert actual is not None
