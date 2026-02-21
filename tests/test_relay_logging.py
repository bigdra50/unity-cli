"""Tests for relay server logging setup."""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from relay.server import (
    LOG_BACKUP_COUNT,
    LOG_MAX_BYTES,
    _resolve_log_level,
    _setup_logging,
    get_log_path,
)


class TestResolveLogLevel:
    def test_debug_flag_returns_debug(self) -> None:
        assert _resolve_log_level(debug_flag=True) == logging.DEBUG

    def test_no_debug_flag_returns_info(self) -> None:
        assert _resolve_log_level(debug_flag=False) == logging.INFO

    def test_env_var_overrides_flag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("UNITY_CLI_LOG", "WARNING")
        assert _resolve_log_level(debug_flag=False) == logging.WARNING

    def test_env_var_case_insensitive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("UNITY_CLI_LOG", "debug")
        assert _resolve_log_level(debug_flag=False) == logging.DEBUG

    def test_invalid_env_var_falls_back_to_info(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("UNITY_CLI_LOG", "INVALID")
        assert _resolve_log_level(debug_flag=False) == logging.INFO


class TestSetupLogging:
    def test_creates_log_dir_and_handlers(self, tmp_path: Path) -> None:
        log_dir = tmp_path / "logs"
        log_file = log_dir / "relay.log"

        with (
            patch("relay.server.LOG_DIR", log_dir),
            patch("relay.server.LOG_FILE", log_file),
        ):
            # Reset root logger handlers
            root = logging.getLogger()
            original_handlers = root.handlers[:]
            root.handlers.clear()

            try:
                _setup_logging(logging.DEBUG)

                assert log_dir.exists()
                handler_types = [type(h).__name__ for h in root.handlers]
                assert "StreamHandler" in handler_types
                assert "RotatingFileHandler" in handler_types
                assert root.level == logging.DEBUG
            finally:
                root.handlers = original_handlers


class TestGetLogPath:
    def test_returns_path(self) -> None:
        path = get_log_path()
        assert path.name == "relay.log"
        assert "unity-cli" in str(path)

    def test_xdg_state_home(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # get_log_path reads module-level LOG_FILE which is computed at import time,
        # so we test the constant directly
        from relay.server import LOG_DIR

        assert str(LOG_DIR).endswith("unity-cli/logs")


class TestLogConstants:
    def test_max_bytes(self) -> None:
        assert LOG_MAX_BYTES == 10 * 1024 * 1024

    def test_backup_count(self) -> None:
        assert LOG_BACKUP_COUNT == 5
