"""Tests for relay server logging setup."""

from __future__ import annotations

import logging
import sys
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

    def test_debug_flag_overrides_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("UNITY_CLI_LOG", "WARNING")
        assert _resolve_log_level(debug_flag=True) == logging.DEBUG


class TestResolveLogDir:
    def test_default_path_unix(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("XDG_STATE_HOME", raising=False)
        if sys.platform == "win32":
            pytest.skip("Unix-specific test")
        log_dir = _resolve_log_dir()
        assert str(log_dir).endswith(".local/state/unity-cli/logs")

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
    def test_default_path_windows_with_localappdata(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.delenv("XDG_STATE_HOME", raising=False)
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        log_dir = _resolve_log_dir()
        assert log_dir == tmp_path / "unity-cli" / "logs"

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
    def test_default_path_windows_without_localappdata(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("XDG_STATE_HOME", raising=False)
        monkeypatch.delenv("LOCALAPPDATA", raising=False)
        log_dir = _resolve_log_dir()
        assert str(log_dir).endswith(str(Path("AppData", "Local", "unity-cli", "logs")))

    def test_xdg_state_home(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        test_state = tmp_path / "xdg-state"
        monkeypatch.setenv("XDG_STATE_HOME", str(test_state))
        log_dir = _resolve_log_dir()
        assert log_dir == test_state / "unity-cli" / "logs"


class TestGetLogPath:
    def test_returns_relay_log(self) -> None:
        path = get_log_path()
        assert path.name == "relay.log"
        assert "unity-cli" in str(path)

    def test_respects_xdg(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        test_state = tmp_path / "xdg"
        monkeypatch.setenv("XDG_STATE_HOME", str(test_state))
        assert get_log_path() == test_state / "unity-cli" / "logs" / "relay.log"


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
        # Use a file as a directory to trigger OSError (cross-platform)
        blocker = tmp_path / "blocker"
        blocker.write_text("block")
        monkeypatch.setenv("XDG_STATE_HOME", str(blocker / "nested"))
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
