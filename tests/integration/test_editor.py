"""Integration tests for EditorAPI commands."""

from __future__ import annotations

import pytest

from unity_cli.api import EditorAPI

pytestmark = pytest.mark.integration


class TestState:
    def test_get_state_returns_valid_response(self, editor: EditorAPI) -> None:
        response = editor.get_state()

        assert "isPlaying" in response
        assert "isPaused" in response

    def test_get_state_not_playing_by_default(self, editor: EditorAPI) -> None:
        response = editor.get_state()

        assert response["isPlaying"] is False


class TestRefresh:
    def test_refresh_succeeds(self, editor: EditorAPI) -> None:
        response = editor.refresh()

        assert isinstance(response, dict)
