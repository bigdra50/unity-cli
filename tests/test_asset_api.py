"""Tests for unity_cli/api/asset.py - Asset API"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from unity_cli.api.asset import AssetAPI


@pytest.fixture
def mock_conn() -> MagicMock:
    """Create a mock relay connection."""
    return MagicMock()


@pytest.fixture
def sut(mock_conn: MagicMock) -> AssetAPI:
    """Create an AssetAPI instance with mock connection."""
    return AssetAPI(mock_conn)


class TestCreatePrefab:
    """create_prefab() メソッドのテスト"""

    def test_sends_asset_command(self, sut: AssetAPI, mock_conn: MagicMock) -> None:
        """Send 'asset' as the command name."""
        mock_conn.send_request.return_value = {}

        sut.create_prefab(path="Assets/Prefabs/Obj.prefab")

        assert mock_conn.send_request.call_args[0][0] == "asset"

    def test_sends_create_prefab_action(self, sut: AssetAPI, mock_conn: MagicMock) -> None:
        """Send action='create_prefab'。"""
        mock_conn.send_request.return_value = {}

        sut.create_prefab(path="Assets/Prefabs/Obj.prefab")

        params = mock_conn.send_request.call_args[0][1]
        assert params["action"] == "create_prefab"

    def test_path_is_required(self, sut: AssetAPI, mock_conn: MagicMock) -> None:
        """path パラメータが含まれる。"""
        mock_conn.send_request.return_value = {}

        sut.create_prefab(path="Assets/Prefabs/Player.prefab")

        params = mock_conn.send_request.call_args[0][1]
        assert params["path"] == "Assets/Prefabs/Player.prefab"

    def test_source_included_when_set(self, sut: AssetAPI, mock_conn: MagicMock) -> None:
        """source 指定時にパラメータに含まれる。"""
        mock_conn.send_request.return_value = {}

        sut.create_prefab(path="Assets/Prefabs/Obj.prefab", source="PlayerObj")

        params = mock_conn.send_request.call_args[0][1]
        assert params["source"] == "PlayerObj"

    def test_source_excluded_when_none(self, sut: AssetAPI, mock_conn: MagicMock) -> None:
        """source=None の場合パラメータに含まれない。"""
        mock_conn.send_request.return_value = {}

        sut.create_prefab(path="Assets/Prefabs/Obj.prefab")

        params = mock_conn.send_request.call_args[0][1]
        assert "source" not in params

    def test_source_id_included_when_set(self, sut: AssetAPI, mock_conn: MagicMock) -> None:
        """source_id 指定時にパラメータに含まれる。"""
        mock_conn.send_request.return_value = {}

        sut.create_prefab(path="Assets/Prefabs/Obj.prefab", source_id=12345)

        params = mock_conn.send_request.call_args[0][1]
        assert params["sourceId"] == 12345

    def test_source_id_excluded_when_none(self, sut: AssetAPI, mock_conn: MagicMock) -> None:
        """source_id=None の場合パラメータに含まれない。"""
        mock_conn.send_request.return_value = {}

        sut.create_prefab(path="Assets/Prefabs/Obj.prefab")

        params = mock_conn.send_request.call_args[0][1]
        assert "sourceId" not in params

    def test_returns_response(self, sut: AssetAPI, mock_conn: MagicMock) -> None:
        """send_request の戻り値をそのまま返す。"""
        expected = {"path": "Assets/Prefabs/Obj.prefab", "guid": "abc123"}
        mock_conn.send_request.return_value = expected

        result = sut.create_prefab(path="Assets/Prefabs/Obj.prefab")
        assert result == expected


class TestCreateScriptableObject:
    """create_scriptable_object() メソッドのテスト"""

    def test_sends_asset_command(self, sut: AssetAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {}

        sut.create_scriptable_object(type_name="GameConfig", path="Assets/Data/Config.asset")

        assert mock_conn.send_request.call_args[0][0] == "asset"

    def test_sends_create_scriptable_object_action(self, sut: AssetAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {}

        sut.create_scriptable_object(type_name="GameConfig", path="Assets/Data/Config.asset")

        params = mock_conn.send_request.call_args[0][1]
        assert params["action"] == "create_scriptable_object"
        assert params["type"] == "GameConfig"
        assert params["path"] == "Assets/Data/Config.asset"

    def test_returns_response(self, sut: AssetAPI, mock_conn: MagicMock) -> None:
        expected = {"path": "Assets/Data/Config.asset"}
        mock_conn.send_request.return_value = expected

        result = sut.create_scriptable_object(type_name="GameConfig", path="Assets/Data/Config.asset")
        assert result == expected


class TestInfo:
    """info() メソッドのテスト"""

    def test_sends_asset_command(self, sut: AssetAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {}

        sut.info(path="Assets/Textures/icon.png")

        assert mock_conn.send_request.call_args[0][0] == "asset"

    def test_sends_info_action(self, sut: AssetAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {}

        sut.info(path="Assets/Textures/icon.png")

        params = mock_conn.send_request.call_args[0][1]
        assert params["action"] == "info"
        assert params["path"] == "Assets/Textures/icon.png"

    def test_returns_response(self, sut: AssetAPI, mock_conn: MagicMock) -> None:
        expected = {"name": "icon", "type": "Texture2D", "guid": "def456"}
        mock_conn.send_request.return_value = expected

        result = sut.info(path="Assets/Textures/icon.png")
        assert result == expected


class TestDeps:
    """deps() メソッドのテスト"""

    def test_sends_deps_action(self, sut: AssetAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {}

        sut.deps(path="Assets/Prefabs/Player.prefab")

        params = mock_conn.send_request.call_args[0][1]
        assert params["action"] == "deps"
        assert params["path"] == "Assets/Prefabs/Player.prefab"

    def test_default_recursive_true(self, sut: AssetAPI, mock_conn: MagicMock) -> None:
        """デフォルトで recursive=True。"""
        mock_conn.send_request.return_value = {}

        sut.deps(path="Assets/Prefabs/Player.prefab")

        params = mock_conn.send_request.call_args[0][1]
        assert params["recursive"] is True

    def test_recursive_false(self, sut: AssetAPI, mock_conn: MagicMock) -> None:
        """recursive=False を指定。"""
        mock_conn.send_request.return_value = {}

        sut.deps(path="Assets/Prefabs/Player.prefab", recursive=False)

        params = mock_conn.send_request.call_args[0][1]
        assert params["recursive"] is False

    def test_returns_response(self, sut: AssetAPI, mock_conn: MagicMock) -> None:
        expected = {"dependencies": ["Assets/Materials/Skin.mat"]}
        mock_conn.send_request.return_value = expected

        result = sut.deps(path="Assets/Prefabs/Player.prefab")
        assert result == expected


class TestRefs:
    """refs() メソッドのテスト"""

    def test_sends_refs_action(self, sut: AssetAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {}

        sut.refs(path="Assets/Materials/Skin.mat")

        params = mock_conn.send_request.call_args[0][1]
        assert params["action"] == "refs"
        assert params["path"] == "Assets/Materials/Skin.mat"

    def test_returns_response(self, sut: AssetAPI, mock_conn: MagicMock) -> None:
        expected = {"referencers": ["Assets/Prefabs/Player.prefab"]}
        mock_conn.send_request.return_value = expected

        result = sut.refs(path="Assets/Materials/Skin.mat")
        assert result == expected
