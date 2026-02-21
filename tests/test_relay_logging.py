"""Tests for relay server logging setup."""

from __future__ import annotations

import logging
from collections.abc import Generator
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pytest

from relay.server import (
    _VALID_LOG_LEVELS,
    LOG_BACKUP_COUNT,
    LOG_MAX_BYTES,
    _resolve_log_dir,
    _resolve_log_level,
    _setup_logging,
    get_log_path,
)


class TestResolveLogLevel:
    def test_debug_flag_returns_debug(self) -> None:
        assert _resolve_log_level(debug_flag=True) == logging.DEBUG

    def test_no_debug_flag_returns_info(self) -> None:
        assert _resolve_log_level(debug_flag=False) == logging.INFO

    @pytest.mark.parametrize(
        ("env_value", "expected"),
        [
            ("DEBUG", logging.DEBUG),
            ("INFO", logging.INFO),
            ("WARNING", logging.WARNING),
            ("ERROR", logging.ERROR),
            ("CRITICAL", logging.CRITICAL),
            ("debug", logging.DEBUG),
            ("warning", logging.WARNING),
        ],
    )
    def test_valid_env_var(self, monkeypatch: pytest.MonkeyPatch, env_value: str, expected: int) -> None:
        monkeypatch.setenv("UNITY_CLI_LOG", env_value)
        assert _resolve_log_level(debug_flag=False) == expected

    @pytest.mark.parametrize("env_value", ["INVALID", "BASIC_FORMAT", "Logger", ""])
    def test_invalid_env_var_falls_back(self, monkeypatch: pytest.MonkeyPatch, env_value: str) -> None:
        monkeypatch.setenv("UNITY_CLI_LOG", env_value)
        # Without debug flag -> INFO
        assert _resolve_log_level(debug_flag=False) == logging.INFO
        # With debug flag -> DEBUG
        assert _resolve_log_level(debug_flag=True) == logging.DEBUG


class TestResolveLogDir:
    def test_default_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("XDG_STATE_HOME", raising=False)
        log_dir = _resolve_log_dir()
        assert str(log_dir).endswith(".local/state/unity-cli/logs")

    def test_xdg_state_home(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("XDG_STATE_HOME", "/tmp/test-xdg-state")
        log_dir = _resolve_log_dir()
        assert log_dir == Path("/tmp/test-xdg-state/unity-cli/logs")


class TestGetLogPath:
    def test_returns_relay_log(self) -> None:
        path = get_log_path()
        assert path.name == "relay.log"
        assert "unity-cli" in str(path)

    def test_respects_xdg(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("XDG_STATE_HOME", "/tmp/test-xdg")
        assert get_log_path() == Path("/tmp/test-xdg/unity-cli/logs/relay.log")


class TestSetupLogging:
    @pytest.fixture(autouse=True)
    def _isolate_root_logger(self) -> Generator[None]:
        """Save and restore root logger state to prevent test pollution."""
        root = logging.getLogger()
        original_handlers = root.handlers[:]
        original_level = root.level
        root.handlers.clear()
        yield
        for handler in root.handlers:
            handler.close()
        root.handlers = original_handlers
        root.level = original_level

    def test_creates_log_dir_and_handlers(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
        _setup_logging(logging.DEBUG)

        log_dir = tmp_path / "unity-cli" / "logs"
        assert log_dir.exists()

        root = logging.getLogger()
        handler_types = [type(h).__name__ for h in root.handlers]
        assert "StreamHandler" in handler_types
        assert "RotatingFileHandler" in handler_types
        assert root.level == logging.DEBUG

    def test_falls_back_to_stderr_on_permission_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # Point to a path that cannot be created
        monkeypatch.setenv("XDG_STATE_HOME", "/proc/nonexistent")
        _setup_logging(logging.INFO)

        root = logging.getLogger()
        handler_types = [type(h).__name__ for h in root.handlers]
        assert "StreamHandler" in handler_types
        assert "RotatingFileHandler" not in handler_types

    def test_force_replaces_existing_handlers(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
        root = logging.getLogger()
        root.addHandler(logging.StreamHandler())

        _setup_logging(logging.WARNING)

        # force=True should have replaced the pre-existing handler
        file_handlers = [h for h in root.handlers if isinstance(h, RotatingFileHandler)]
        assert len(file_handlers) == 1
        assert root.level == logging.WARNING

    def test_delay_true(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
        _setup_logging(logging.INFO)

        root = logging.getLogger()
        file_handlers = [h for h in root.handlers if isinstance(h, RotatingFileHandler)]
        assert len(file_handlers) == 1
        # delay=True means the file is not opened until first emit
        log_file = tmp_path / "unity-cli" / "logs" / "relay.log"
        assert not log_file.exists()


class TestLogConstants:
    def test_max_bytes(self) -> None:
        assert LOG_MAX_BYTES == 10 * 1024 * 1024

    def test_backup_count(self) -> None:
        assert LOG_BACKUP_COUNT == 5

    def test_valid_levels_complete(self) -> None:
        assert {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"} == _VALID_LOG_LEVELS
