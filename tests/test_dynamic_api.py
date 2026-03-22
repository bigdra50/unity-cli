"""Tests for unity_cli/api/dynamic_api.py - Dynamic API"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from unity_cli.api.dynamic_api import DynamicAPI
from unity_cli.api.schema_cache import SchemaCache
from unity_cli.exceptions import UnityCLIError


@pytest.fixture
def mock_conn() -> MagicMock:
    """Create a mock relay connection."""
    conn = MagicMock()
    conn.list_instances.return_value = [{"unity_version": "6000.2.6f2"}]
    return conn


@pytest.fixture
def sut(mock_conn: MagicMock, tmp_path: Path) -> DynamicAPI:
    """Create a DynamicAPI instance with mock connection and temp cache."""
    api = DynamicAPI(mock_conn)
    api._cache = SchemaCache(cache_dir=tmp_path / "api-schema")
    return api


FULL_SCHEMA: dict = {
    "methods": [
        {"type": "UnityEditor.AssetDatabase", "method": "Refresh", "returnType": "Void", "parameters": []},
        {
            "type": "UnityEditor.AssetDatabase",
            "method": "ImportAsset",
            "returnType": "Void",
            "parameters": [{"name": "path", "type": "String", "hasDefault": False}],
        },
        {"type": "UnityEngine.Application", "method": "get_dataPath", "returnType": "String", "parameters": []},
    ],
    "total": 3,
    "hasMore": False,
}


class TestInvoke:
    """invoke() method tests."""

    def test_invoke_sends_api_invoke_command(self, sut: DynamicAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {}
        sut.invoke("UnityEditor.AssetDatabase", "Refresh")
        assert mock_conn.send_request.call_args[0][0] == "api-invoke"

    def test_invoke_sends_type_and_method(self, sut: DynamicAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {}
        sut.invoke("UnityEngine.Application", "get_dataPath")
        params = mock_conn.send_request.call_args[0][1]
        assert params["type"] == "UnityEngine.Application"
        assert params["method"] == "get_dataPath"

    def test_invoke_sends_empty_params_by_default(self, sut: DynamicAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {}
        sut.invoke("UnityEditor.AssetDatabase", "Refresh")
        params = mock_conn.send_request.call_args[0][1]
        assert params["params"] == []

    def test_invoke_sends_custom_params(self, sut: DynamicAPI, mock_conn: MagicMock) -> None:
        mock_conn.send_request.return_value = {}
        sut.invoke("UnityEditor.AssetDatabase", "ImportAsset", ["Assets/test.prefab", 0])
        params = mock_conn.send_request.call_args[0][1]
        assert params["params"] == ["Assets/test.prefab", 0]

    def test_invoke_returns_response(self, sut: DynamicAPI, mock_conn: MagicMock) -> None:
        expected = {
            "type": "UnityEngine.Application",
            "method": "get_unityVersion",
            "returnType": "String",
            "result": "6000.1.1f1",
        }
        mock_conn.send_request.return_value = expected
        result = sut.invoke("UnityEngine.Application", "get_unityVersion")
        assert result == expected


class TestSchema:
    """schema() method tests."""

    def test_schema_sends_cache_all(self, sut: DynamicAPI, mock_conn: MagicMock) -> None:
        """Fetch full schema with cache_all=True."""
        mock_conn.send_request.return_value = FULL_SCHEMA
        sut.schema(no_cache=True)
        params = mock_conn.send_request.call_args[0][1]
        assert params["cache_all"] is True

    def test_schema_caches_result(self, sut: DynamicAPI, mock_conn: MagicMock) -> None:
        """Cache schema after Relay fetch."""
        mock_conn.send_request.return_value = {**FULL_SCHEMA}
        sut.schema(no_cache=True)
        assert sut._cache.has("6000.2.6f2")

    def test_schema_uses_cache(self, sut: DynamicAPI, mock_conn: MagicMock) -> None:
        """Use cached schema without hitting Relay."""
        sut._cache.put("6000.2.6f2", FULL_SCHEMA)
        result = sut.schema()
        mock_conn.send_request.assert_not_called()
        assert result["total"] == 3

    def test_schema_filters_by_namespace(self, sut: DynamicAPI, mock_conn: MagicMock) -> None:
        """Filter results by namespace prefix."""
        sut._cache.put("6000.2.6f2", FULL_SCHEMA)
        result = sut.schema(namespace=["UnityEditor"])
        assert all(m["type"].startswith("UnityEditor") for m in result["methods"])
        assert result["total"] == 2

    def test_schema_filters_by_type(self, sut: DynamicAPI, mock_conn: MagicMock) -> None:
        """Filter results by type name."""
        sut._cache.put("6000.2.6f2", FULL_SCHEMA)
        result = sut.schema(type_name="Application")
        assert result["total"] == 1
        assert result["methods"][0]["type"] == "UnityEngine.Application"

    def test_schema_filters_by_method(self, sut: DynamicAPI, mock_conn: MagicMock) -> None:
        """Filter results by method name."""
        sut._cache.put("6000.2.6f2", FULL_SCHEMA)
        result = sut.schema(method_name="Refresh")
        assert result["total"] == 1

    def test_schema_paginates(self, sut: DynamicAPI, mock_conn: MagicMock) -> None:
        """Paginate results with limit and offset."""
        sut._cache.put("6000.2.6f2", FULL_SCHEMA)
        result = sut.schema(limit=1, offset=0)
        assert len(result["methods"]) == 1
        assert result["total"] == 3
        assert result["hasMore"] is True

    def test_schema_offline_with_cache(self, sut: DynamicAPI, mock_conn: MagicMock) -> None:
        """Offline mode returns cached schema."""
        sut._cache.put("6000.2.6f2", FULL_SCHEMA)
        result = sut.schema(offline=True)
        mock_conn.send_request.assert_not_called()
        assert result["total"] == 3

    def test_schema_offline_without_cache_raises(self, sut: DynamicAPI, mock_conn: MagicMock) -> None:
        """Offline mode without cache raises error."""
        with pytest.raises(UnityCLIError, match="CACHE_MISS"):
            sut.schema(offline=True)

    def test_schema_no_cache_forces_relay(self, sut: DynamicAPI, mock_conn: MagicMock) -> None:
        """no_cache skips cache and fetches from Relay."""
        sut._cache.put("6000.2.6f2", FULL_SCHEMA)
        mock_conn.send_request.return_value = {**FULL_SCHEMA, "total": 999}
        sut.schema(no_cache=True)
        mock_conn.send_request.assert_called_once()
