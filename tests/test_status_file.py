"""Tests for relay/status_file.py - Status file reading"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from relay.status_file import (
    StatusFileContent,
    compute_instance_hash,
    get_status_dir,
    is_instance_reloading,
    read_status_file,
)


class TestStatusFilePath:
    """Test status file path computation"""

    def test_get_status_dir_returns_default_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("UNITY_BRIDGE_STATUS_DIR", raising=False)

        result = get_status_dir()

        assert result.name == ".unity-bridge"
        assert result.parent.name == result.home().name

    def test_get_status_dir_respects_env_var(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
    ) -> None:
        custom_dir = str(tmp_path)
        monkeypatch.setenv("UNITY_BRIDGE_STATUS_DIR", custom_dir)

        result = get_status_dir()

        assert str(result) == custom_dir

    def test_compute_instance_hash_is_deterministic(self) -> None:
        instance_id = "/Users/dev/MyProject"

        hash1 = compute_instance_hash(instance_id)
        hash2 = compute_instance_hash(instance_id)

        assert hash1 == hash2

    def test_compute_instance_hash_produces_8_char_hex(self) -> None:
        instance_id = "/Users/dev/MyProject"

        result = compute_instance_hash(instance_id)

        assert len(result) == 8
        # Verify it's valid hex
        int(result, 16)


class TestReadStatusFile:
    """Test status file reading"""

    def test_read_nonexistent_file_returns_none(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
    ) -> None:
        monkeypatch.setenv("UNITY_BRIDGE_STATUS_DIR", str(tmp_path))

        result = read_status_file("/nonexistent/project")

        assert result is None

    def test_read_valid_status_file(self, monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory) -> None:
        monkeypatch.setenv("UNITY_BRIDGE_STATUS_DIR", str(tmp_path))

        instance_id = "/Users/dev/MyProject"
        hash_str = compute_instance_hash(instance_id)
        status_file = tmp_path / f"status-{hash_str}.json"

        status_data = {
            "instance_id": instance_id,
            "project_name": "MyProject",
            "unity_version": "2022.3.20f1",
            "status": "ready",
            "relay_host": "127.0.0.1",
            "relay_port": 6500,
            "timestamp": "2024-01-15T10:30:00Z",
            "seq": 42,
        }
        status_file.write_text(json.dumps(status_data))

        result = read_status_file(instance_id)

        assert result is not None
        assert isinstance(result, StatusFileContent)
        assert result.instance_id == instance_id
        assert result.project_name == "MyProject"
        assert result.unity_version == "2022.3.20f1"
        assert result.status == "ready"
        assert result.relay_host == "127.0.0.1"
        assert result.relay_port == 6500
        assert result.seq == 42

    def test_read_invalid_json_returns_none(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
    ) -> None:
        monkeypatch.setenv("UNITY_BRIDGE_STATUS_DIR", str(tmp_path))

        instance_id = "/Users/dev/MyProject"
        hash_str = compute_instance_hash(instance_id)
        status_file = tmp_path / f"status-{hash_str}.json"
        status_file.write_text("{ invalid json }")

        result = read_status_file(instance_id)

        assert result is None


class TestIsInstanceReloading:
    """Test is_instance_reloading function"""

    def test_returns_false_for_nonexistent_file(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
    ) -> None:
        monkeypatch.setenv("UNITY_BRIDGE_STATUS_DIR", str(tmp_path))

        result = is_instance_reloading("/nonexistent/project")

        assert result is False

    def test_returns_true_for_reloading_status(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
    ) -> None:
        monkeypatch.setenv("UNITY_BRIDGE_STATUS_DIR", str(tmp_path))

        instance_id = "/Users/dev/MyProject"
        hash_str = compute_instance_hash(instance_id)
        status_file = tmp_path / f"status-{hash_str}.json"

        # Use a recent timestamp
        recent_timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        status_data = {
            "instance_id": instance_id,
            "project_name": "MyProject",
            "unity_version": "2022.3.20f1",
            "status": "reloading",
            "relay_host": "127.0.0.1",
            "relay_port": 6500,
            "timestamp": recent_timestamp,
            "seq": 1,
        }
        status_file.write_text(json.dumps(status_data))

        result = is_instance_reloading(instance_id)

        assert result is True

    def test_returns_false_for_ready_status(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
    ) -> None:
        monkeypatch.setenv("UNITY_BRIDGE_STATUS_DIR", str(tmp_path))

        instance_id = "/Users/dev/MyProject"
        hash_str = compute_instance_hash(instance_id)
        status_file = tmp_path / f"status-{hash_str}.json"

        recent_timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        status_data = {
            "instance_id": instance_id,
            "project_name": "MyProject",
            "unity_version": "2022.3.20f1",
            "status": "ready",
            "relay_host": "127.0.0.1",
            "relay_port": 6500,
            "timestamp": recent_timestamp,
            "seq": 1,
        }
        status_file.write_text(json.dumps(status_data))

        result = is_instance_reloading(instance_id)

        assert result is False

    def test_returns_false_for_stale_file(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
    ) -> None:
        monkeypatch.setenv("UNITY_BRIDGE_STATUS_DIR", str(tmp_path))

        instance_id = "/Users/dev/MyProject"
        hash_str = compute_instance_hash(instance_id)
        status_file = tmp_path / f"status-{hash_str}.json"

        # Use a timestamp older than 120 seconds
        stale_timestamp = (datetime.now(UTC) - timedelta(seconds=150)).isoformat().replace("+00:00", "Z")
        status_data = {
            "instance_id": instance_id,
            "project_name": "MyProject",
            "unity_version": "2022.3.20f1",
            "status": "reloading",
            "relay_host": "127.0.0.1",
            "relay_port": 6500,
            "timestamp": stale_timestamp,
            "seq": 1,
        }
        status_file.write_text(json.dumps(status_data))

        result = is_instance_reloading(instance_id)

        assert result is False
