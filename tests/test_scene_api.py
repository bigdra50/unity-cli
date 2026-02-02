"""Tests for unity_cli/api/scene.py - Scene API"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from unity_cli.api.scene import SceneAPI


@pytest.fixture
def mock_conn() -> MagicMock:
    """Create a mock relay connection."""
    return MagicMock()


@pytest.fixture
def sut(mock_conn: MagicMock) -> SceneAPI:
    """Create a SceneAPI instance with mock connection."""
    return SceneAPI(mock_conn)


class TestGetActive:
    """get_active() メソッドのテスト"""

    def test_get_active_sends_scene_command(self, sut: SceneAPI, mock_conn: MagicMock) -> None:
        """Send 'scene' as the command name."""
        mock_conn.send_request.return_value = {}

        sut.get_active()

        assert mock_conn.send_request.call_args[0][0] == "scene"

    def test_get_active_sends_active_action(self, sut: SceneAPI, mock_conn: MagicMock) -> None:
        """Send action='active' to get active scene info."""
        mock_conn.send_request.return_value = {}

        sut.get_active()

        params = mock_conn.send_request.call_args[0][1]
        assert params == {"action": "active"}

    def test_get_active_returns_response(self, sut: SceneAPI, mock_conn: MagicMock) -> None:
        """Return the active scene response."""
        expected = {"name": "SampleScene", "path": "Assets/Scenes/SampleScene.unity"}
        mock_conn.send_request.return_value = expected

        result = sut.get_active()

        assert result == expected


class TestGetHierarchy:
    """get_hierarchy() メソッドのテスト"""

    def test_get_hierarchy_sends_hierarchy_action(self, sut: SceneAPI, mock_conn: MagicMock) -> None:
        """Send action='hierarchy' to get scene hierarchy."""
        mock_conn.send_request.return_value = {}

        sut.get_hierarchy()

        params = mock_conn.send_request.call_args[0][1]
        assert params["action"] == "hierarchy"

    def test_get_hierarchy_default_params(self, sut: SceneAPI, mock_conn: MagicMock) -> None:
        """Default depth=1, page_size=50, cursor=0."""
        mock_conn.send_request.return_value = {}

        sut.get_hierarchy()

        params = mock_conn.send_request.call_args[0][1]
        assert params["depth"] == 1
        assert params["page_size"] == 50
        assert params["cursor"] == 0

    def test_get_hierarchy_with_custom_depth(self, sut: SceneAPI, mock_conn: MagicMock) -> None:
        """Send custom depth value."""
        mock_conn.send_request.return_value = {}

        sut.get_hierarchy(depth=3)

        params = mock_conn.send_request.call_args[0][1]
        assert params["depth"] == 3

    def test_get_hierarchy_with_pagination(self, sut: SceneAPI, mock_conn: MagicMock) -> None:
        """Send custom page_size and cursor."""
        mock_conn.send_request.return_value = {}

        sut.get_hierarchy(page_size=20, cursor=5)

        params = mock_conn.send_request.call_args[0][1]
        assert params["page_size"] == 20
        assert params["cursor"] == 5


class TestLoad:
    """load() メソッドのテスト"""

    def test_load_sends_load_action(self, sut: SceneAPI, mock_conn: MagicMock) -> None:
        """Send action='load' to load a scene."""
        mock_conn.send_request.return_value = {}

        sut.load(name="Main")

        params = mock_conn.send_request.call_args[0][1]
        assert params["action"] == "load"

    def test_load_by_name(self, sut: SceneAPI, mock_conn: MagicMock) -> None:
        """Include name key when name is provided."""
        mock_conn.send_request.return_value = {}

        sut.load(name="Main")

        params = mock_conn.send_request.call_args[0][1]
        assert params["name"] == "Main"

    def test_load_by_path(self, sut: SceneAPI, mock_conn: MagicMock) -> None:
        """Include path key when path is provided."""
        mock_conn.send_request.return_value = {}

        sut.load(path="Assets/Scenes/Main.unity")

        params = mock_conn.send_request.call_args[0][1]
        assert params["path"] == "Assets/Scenes/Main.unity"

    def test_load_additive(self, sut: SceneAPI, mock_conn: MagicMock) -> None:
        """Set additive=True for additive scene loading."""
        mock_conn.send_request.return_value = {}

        sut.load(name="UI", additive=True)

        params = mock_conn.send_request.call_args[0][1]
        assert params["additive"] is True

    def test_load_default_not_additive(self, sut: SceneAPI, mock_conn: MagicMock) -> None:
        """Default additive is False."""
        mock_conn.send_request.return_value = {}

        sut.load(name="Main")

        params = mock_conn.send_request.call_args[0][1]
        assert params["additive"] is False

    def test_load_without_name_excludes_name_key(self, sut: SceneAPI, mock_conn: MagicMock) -> None:
        """Exclude name key when name is not provided."""
        mock_conn.send_request.return_value = {}

        sut.load(path="Assets/Scenes/Main.unity")

        params = mock_conn.send_request.call_args[0][1]
        assert "name" not in params


class TestSave:
    """save() メソッドのテスト"""

    def test_save_sends_save_action(self, sut: SceneAPI, mock_conn: MagicMock) -> None:
        """Send action='save' to save current scene."""
        mock_conn.send_request.return_value = {}

        sut.save()

        params = mock_conn.send_request.call_args[0][1]
        assert params["action"] == "save"

    def test_save_with_path(self, sut: SceneAPI, mock_conn: MagicMock) -> None:
        """Include path key when save path is provided."""
        mock_conn.send_request.return_value = {}

        sut.save(path="Assets/Scenes/NewScene.unity")

        params = mock_conn.send_request.call_args[0][1]
        assert params["path"] == "Assets/Scenes/NewScene.unity"

    def test_save_without_path_excludes_path_key(self, sut: SceneAPI, mock_conn: MagicMock) -> None:
        """Exclude path key when path is not provided."""
        mock_conn.send_request.return_value = {}

        sut.save()

        params = mock_conn.send_request.call_args[0][1]
        assert "path" not in params
