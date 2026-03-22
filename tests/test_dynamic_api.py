"""Tests for unity_cli/api/dynamic_api.py - Dynamic API"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from unity_cli.api.dynamic_api import DynamicAPI


@pytest.fixture
def mock_conn() -> MagicMock:
    """Create a mock relay connection."""
    return MagicMock()


@pytest.fixture
def sut(mock_conn: MagicMock) -> DynamicAPI:
    """Create a DynamicAPI instance with mock connection."""
    return DynamicAPI(mock_conn)


class TestInvoke:
    """invoke() method tests."""

    def test_invoke_sends_api_invoke_command(self, sut: DynamicAPI, mock_conn: MagicMock) -> None:
        """Send 'api-invoke' as the command name."""
        mock_conn.send_request.return_value = {}

        sut.invoke("UnityEditor.AssetDatabase", "Refresh")

        assert mock_conn.send_request.call_args[0][0] == "api-invoke"

    def test_invoke_sends_type_and_method(self, sut: DynamicAPI, mock_conn: MagicMock) -> None:
        """Send type and method in params."""
        mock_conn.send_request.return_value = {}

        sut.invoke("UnityEngine.Application", "get_dataPath")

        params = mock_conn.send_request.call_args[0][1]
        assert params["type"] == "UnityEngine.Application"
        assert params["method"] == "get_dataPath"

    def test_invoke_sends_empty_params_by_default(self, sut: DynamicAPI, mock_conn: MagicMock) -> None:
        """Send empty params list when no args provided."""
        mock_conn.send_request.return_value = {}

        sut.invoke("UnityEditor.AssetDatabase", "Refresh")

        params = mock_conn.send_request.call_args[0][1]
        assert params["params"] == []

    def test_invoke_sends_custom_params(self, sut: DynamicAPI, mock_conn: MagicMock) -> None:
        """Send custom params when provided."""
        mock_conn.send_request.return_value = {}

        sut.invoke("UnityEditor.AssetDatabase", "ImportAsset", ["Assets/test.prefab", 0])

        params = mock_conn.send_request.call_args[0][1]
        assert params["params"] == ["Assets/test.prefab", 0]

    def test_invoke_returns_response(self, sut: DynamicAPI, mock_conn: MagicMock) -> None:
        """Return the response from send_request."""
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

    def test_schema_sends_api_schema_command(self, sut: DynamicAPI, mock_conn: MagicMock) -> None:
        """Send 'api-schema' as the command name."""
        mock_conn.send_request.return_value = {}

        sut.schema()

        assert mock_conn.send_request.call_args[0][0] == "api-schema"

    def test_schema_default_limit_100(self, sut: DynamicAPI, mock_conn: MagicMock) -> None:
        """Default limit is 100."""
        mock_conn.send_request.return_value = {}

        sut.schema()

        params = mock_conn.send_request.call_args[0][1]
        assert params["limit"] == 100

    def test_schema_default_offset_0(self, sut: DynamicAPI, mock_conn: MagicMock) -> None:
        """Default offset is 0."""
        mock_conn.send_request.return_value = {}

        sut.schema()

        params = mock_conn.send_request.call_args[0][1]
        assert params["offset"] == 0

    def test_schema_with_namespace_filter(self, sut: DynamicAPI, mock_conn: MagicMock) -> None:
        """Include namespace filter when provided."""
        mock_conn.send_request.return_value = {}

        sut.schema(namespace=["UnityEditor"])

        params = mock_conn.send_request.call_args[0][1]
        assert params["namespace"] == ["UnityEditor"]

    def test_schema_with_type_filter(self, sut: DynamicAPI, mock_conn: MagicMock) -> None:
        """Include type filter when provided."""
        mock_conn.send_request.return_value = {}

        sut.schema(type_name="AssetDatabase")

        params = mock_conn.send_request.call_args[0][1]
        assert params["type"] == "AssetDatabase"

    def test_schema_with_method_filter(self, sut: DynamicAPI, mock_conn: MagicMock) -> None:
        """Include method filter when provided."""
        mock_conn.send_request.return_value = {}

        sut.schema(method_name="Refresh")

        params = mock_conn.send_request.call_args[0][1]
        assert params["method"] == "Refresh"

    def test_schema_with_pagination(self, sut: DynamicAPI, mock_conn: MagicMock) -> None:
        """Send custom limit and offset."""
        mock_conn.send_request.return_value = {}

        sut.schema(limit=50, offset=200)

        params = mock_conn.send_request.call_args[0][1]
        assert params["limit"] == 50
        assert params["offset"] == 200

    def test_schema_without_filters_excludes_optional_keys(self, sut: DynamicAPI, mock_conn: MagicMock) -> None:
        """Exclude namespace/type/method keys when not provided."""
        mock_conn.send_request.return_value = {}

        sut.schema()

        params = mock_conn.send_request.call_args[0][1]
        assert "namespace" not in params
        assert "type" not in params
        assert "method" not in params

    def test_schema_returns_response(self, sut: DynamicAPI, mock_conn: MagicMock) -> None:
        """Return the response from send_request."""
        expected = {"methods": [], "total": 0, "hasMore": False}
        mock_conn.send_request.return_value = expected

        result = sut.schema()

        assert result == expected
