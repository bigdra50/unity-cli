"""Tests for server detail sanitization and BUSY reset logic."""

from __future__ import annotations

import pytest

from relay.server import _sanitize_detail


class TestSanitizeDetail:
    """Test _sanitize_detail allowlist validation."""

    @pytest.mark.parametrize(
        "value",
        ["compiling", "running_tests", "asset_import", "playmode_transition"],
    )
    def test_valid_detail_passes(self, value: str) -> None:
        assert _sanitize_detail(value) == value

    def test_none_returns_none(self) -> None:
        assert _sanitize_detail(None) is None

    def test_empty_string_returns_none(self) -> None:
        assert _sanitize_detail("") is None

    def test_unknown_detail_returns_none(self) -> None:
        assert _sanitize_detail("unknown_phase") is None

    def test_non_string_returns_none(self) -> None:
        assert _sanitize_detail(42) is None

    def test_long_string_returns_none(self) -> None:
        assert _sanitize_detail("a" * 100) is None

    def test_control_chars_returns_none(self) -> None:
        assert _sanitize_detail("compiling\x00") is None

    def test_ansi_escape_returns_none(self) -> None:
        assert _sanitize_detail("\x1b[31mred\x1b[0m") is None

    def test_whitespace_stripped(self) -> None:
        assert _sanitize_detail("  compiling  ") == "compiling"
