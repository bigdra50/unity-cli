"""Tests for version mismatch detection and update checker."""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from relay.instance_registry import UnityInstance
from relay.protocol import RegisterMessage, ResponseMessage


class TestRegisterMessageBridgeVersion:
    """Test bridge_version field in RegisterMessage"""

    def test_default_bridge_version_is_empty(self) -> None:
        msg = RegisterMessage()
        assert msg.bridge_version == ""

    def test_bridge_version_in_to_dict(self) -> None:
        msg = RegisterMessage(
            instance_id="/Users/dev/MyGame",
            project_name="MyGame",
            unity_version="2022.3.20f1",
            bridge_version="3.5.2",
        )
        d = msg.to_dict()
        assert d["bridge_version"] == "3.5.2"

    def test_backwards_compatible_without_bridge_version(self) -> None:
        msg = RegisterMessage(
            instance_id="/test",
            project_name="Test",
            unity_version="2022.3",
        )
        d = msg.to_dict()
        assert d["bridge_version"] == ""


class TestResponseMessageVersionFields:
    """Test version fields in ResponseMessage"""

    def test_default_version_fields_are_empty(self) -> None:
        msg = ResponseMessage(id="test-id")
        assert msg.relay_version == ""
        assert msg.bridge_version == ""

    def test_version_fields_in_to_dict(self) -> None:
        msg = ResponseMessage(
            id="test-id",
            success=True,
            relay_version="3.5.2",
            bridge_version="3.5.1",
        )
        d = msg.to_dict()
        assert d["relay_version"] == "3.5.2"
        assert d["bridge_version"] == "3.5.1"

    def test_backwards_compatible_empty_versions(self) -> None:
        msg = ResponseMessage(id="test-id", success=True)
        d = msg.to_dict()
        assert d["relay_version"] == ""
        assert d["bridge_version"] == ""


class TestUnityInstanceBridgeVersion:
    """Test bridge_version in UnityInstance"""

    def test_default_bridge_version(self) -> None:
        instance = UnityInstance(
            instance_id="/test",
            project_name="Test",
            unity_version="2022.3",
        )
        assert instance.bridge_version == ""

    def test_bridge_version_in_to_dict(self) -> None:
        instance = UnityInstance(
            instance_id="/test",
            project_name="Test",
            unity_version="2022.3",
            bridge_version="3.5.2",
        )
        d = instance.to_dict()
        assert d["bridge_version"] == "3.5.2"

    def test_bridge_version_set_on_init(self) -> None:
        instance = UnityInstance(
            instance_id="/test",
            project_name="Test",
            unity_version="2022.3",
            bridge_version="3.4.0",
        )
        assert instance.bridge_version == "3.4.0"


class TestUpdateChecker:
    """Test update_checker module"""

    def test_get_latest_version_cached_no_file(self, tmp_path: Path) -> None:
        from unity_cli.update_checker import get_latest_version_cached

        with patch("unity_cli.update_checker.CACHE_FILE", tmp_path / "nonexistent.json"):
            assert get_latest_version_cached() is None

    def test_get_latest_version_cached_valid(self, tmp_path: Path) -> None:
        from unity_cli.update_checker import get_latest_version_cached

        cache_file = tmp_path / "update-check.json"
        cache_file.write_text(json.dumps({"latest_version": "4.0.0", "checked_at": time.time()}))
        with patch("unity_cli.update_checker.CACHE_FILE", cache_file):
            assert get_latest_version_cached() == "4.0.0"

    def test_get_latest_version_cached_expired(self, tmp_path: Path) -> None:
        from unity_cli.update_checker import get_latest_version_cached

        cache_file = tmp_path / "update-check.json"
        cache_file.write_text(json.dumps({"latest_version": "4.0.0", "checked_at": time.time() - 100000}))
        with patch("unity_cli.update_checker.CACHE_FILE", cache_file):
            assert get_latest_version_cached() is None

    def test_get_update_message_no_update(self, tmp_path: Path) -> None:
        from unity_cli.update_checker import get_update_message

        cache_file = tmp_path / "update-check.json"
        cache_file.write_text(json.dumps({"latest_version": "3.5.2", "checked_at": time.time()}))
        with patch("unity_cli.update_checker.CACHE_FILE", cache_file):
            assert get_update_message("3.5.2") is None

    def test_get_update_message_update_available(self, tmp_path: Path) -> None:
        from unity_cli.update_checker import get_update_message

        cache_file = tmp_path / "update-check.json"
        cache_file.write_text(json.dumps({"latest_version": "4.0.0", "checked_at": time.time()}))
        with patch("unity_cli.update_checker.CACHE_FILE", cache_file):
            msg = get_update_message("3.5.2")
            assert msg is not None
            assert "4.0.0" in msg
            assert "3.5.2" in msg

    def test_get_update_message_empty_current(self, tmp_path: Path) -> None:
        from unity_cli.update_checker import get_update_message

        cache_file = tmp_path / "update-check.json"
        cache_file.write_text(json.dumps({"latest_version": "4.0.0", "checked_at": time.time()}))
        with patch("unity_cli.update_checker.CACHE_FILE", cache_file):
            assert get_update_message("") is None

    def test_start_update_check_skips_when_cached(self, tmp_path: Path) -> None:
        from unity_cli.update_checker import start_update_check

        cache_file = tmp_path / "update-check.json"
        cache_file.write_text(json.dumps({"latest_version": "4.0.0", "checked_at": time.time()}))
        with (
            patch("unity_cli.update_checker.CACHE_FILE", cache_file),
            patch("unity_cli.update_checker.threading.Thread") as mock_thread,
        ):
            start_update_check()
            mock_thread.assert_not_called()


class TestVersionInfoCallback:
    """Test version info callback in RelayConnection"""

    def test_version_info_called_on_first_response(self) -> None:
        from unity_cli.client import RelayConnection

        callback = MagicMock()
        conn = RelayConnection(on_version_info=callback)

        response = {
            "type": "RESPONSE",
            "id": "test",
            "success": True,
            "data": {},
            "relay_version": "3.5.2",
            "bridge_version": "3.5.1",
        }
        conn._handle_response(response, "test_cmd")
        callback.assert_called_once_with("3.5.2", "3.5.1")

    def test_version_info_called_only_once(self) -> None:
        from unity_cli.client import RelayConnection

        callback = MagicMock()
        conn = RelayConnection(on_version_info=callback)

        response = {
            "type": "RESPONSE",
            "id": "test",
            "success": True,
            "data": {},
            "relay_version": "3.5.2",
            "bridge_version": "3.5.1",
        }
        conn._handle_response(response, "test_cmd")
        conn._handle_response(response, "test_cmd2")
        callback.assert_called_once()

    def test_version_info_not_called_when_empty(self) -> None:
        from unity_cli.client import RelayConnection

        callback = MagicMock()
        conn = RelayConnection(on_version_info=callback)

        response = {
            "type": "RESPONSE",
            "id": "test",
            "success": True,
            "data": {},
        }
        conn._handle_response(response, "test_cmd")
        callback.assert_not_called()

    def test_version_info_not_called_on_error(self) -> None:
        from unity_cli.client import RelayConnection
        from unity_cli.exceptions import UnityCLIError

        callback = MagicMock()
        conn = RelayConnection(on_version_info=callback)

        response = {
            "type": "ERROR",
            "id": "test",
            "error": {"code": "INTERNAL_ERROR", "message": "fail"},
        }
        with pytest.raises(UnityCLIError):
            conn._handle_response(response, "test_cmd")
        callback.assert_not_called()
