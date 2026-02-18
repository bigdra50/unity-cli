"""Tests for output module: OutputMode resolution and plain-text helpers."""

from __future__ import annotations

import os
import sys
from unittest.mock import patch

import pytest

from unity_cli.cli.output import (
    OutputConfig,
    OutputMode,
    _print_plain_table,
    configure_output,
    print_error,
    print_info,
    print_key_value,
    print_line,
    print_success,
    print_warning,
    resolve_output_mode,
    set_quiet,
)

# =============================================================================
# resolve_output_mode
# =============================================================================


class TestResolveOutputMode:
    def test_pretty_flag_true(self) -> None:
        assert resolve_output_mode(pretty_flag=True) is OutputMode.PRETTY

    def test_pretty_flag_false(self) -> None:
        assert resolve_output_mode(pretty_flag=False) is OutputMode.PLAIN

    def test_env_unity_cli_json(self) -> None:
        with patch.dict(os.environ, {"UNITY_CLI_JSON": "1"}, clear=False):
            assert resolve_output_mode() is OutputMode.JSON

    def test_env_unity_cli_json_zero_ignored(self) -> None:
        env = {k: v for k, v in os.environ.items() if k not in ("UNITY_CLI_JSON", "UNITY_CLI_NO_PRETTY", "NO_COLOR")}
        with (
            patch.dict(os.environ, {**env, "UNITY_CLI_JSON": "0"}, clear=True),
            patch.object(sys.stdout, "isatty", return_value=False),
        ):
            assert resolve_output_mode() is OutputMode.PLAIN

    def test_env_unity_cli_json_false_ignored(self) -> None:
        env = {k: v for k, v in os.environ.items() if k not in ("UNITY_CLI_JSON", "UNITY_CLI_NO_PRETTY", "NO_COLOR")}
        with (
            patch.dict(os.environ, {**env, "UNITY_CLI_JSON": "false"}, clear=True),
            patch.object(sys.stdout, "isatty", return_value=False),
        ):
            assert resolve_output_mode() is OutputMode.PLAIN

    def test_env_unity_cli_no_pretty(self) -> None:
        env = {k: v for k, v in os.environ.items() if k not in ("UNITY_CLI_JSON", "UNITY_CLI_NO_PRETTY", "NO_COLOR")}
        with patch.dict(os.environ, {**env, "UNITY_CLI_NO_PRETTY": "1"}, clear=True):
            assert resolve_output_mode() is OutputMode.PLAIN

    def test_env_no_color(self) -> None:
        env = {k: v for k, v in os.environ.items() if k not in ("UNITY_CLI_JSON", "UNITY_CLI_NO_PRETTY", "NO_COLOR")}
        with patch.dict(os.environ, {**env, "NO_COLOR": ""}, clear=True):
            assert resolve_output_mode() is OutputMode.PLAIN

    def test_tty_true_returns_pretty(self) -> None:
        env = {k: v for k, v in os.environ.items() if k not in ("UNITY_CLI_JSON", "UNITY_CLI_NO_PRETTY", "NO_COLOR")}
        with patch.dict(os.environ, env, clear=True), patch.object(sys.stdout, "isatty", return_value=True):
            assert resolve_output_mode() is OutputMode.PRETTY

    def test_tty_false_returns_plain(self) -> None:
        env = {k: v for k, v in os.environ.items() if k not in ("UNITY_CLI_JSON", "UNITY_CLI_NO_PRETTY", "NO_COLOR")}
        with patch.dict(os.environ, env, clear=True), patch.object(sys.stdout, "isatty", return_value=False):
            assert resolve_output_mode() is OutputMode.PLAIN

    def test_pretty_flag_overrides_env_no_color(self) -> None:
        with patch.dict(os.environ, {"NO_COLOR": ""}, clear=False):
            assert resolve_output_mode(pretty_flag=True) is OutputMode.PRETTY


# =============================================================================
# OutputConfig
# =============================================================================


class TestOutputConfig:
    def test_is_json(self) -> None:
        cfg = OutputConfig(mode=OutputMode.JSON)
        assert cfg.is_json
        assert not cfg.is_plain
        assert not cfg.is_pretty

    def test_is_plain(self) -> None:
        cfg = OutputConfig(mode=OutputMode.PLAIN)
        assert cfg.is_plain
        assert not cfg.is_json
        assert not cfg.is_pretty

    def test_is_pretty(self) -> None:
        cfg = OutputConfig(mode=OutputMode.PRETTY)
        assert cfg.is_pretty
        assert not cfg.is_json
        assert not cfg.is_plain


# =============================================================================
# Plain-text output helpers
# =============================================================================


class TestPlainTextOutput:
    def setup_method(self) -> None:
        configure_output(OutputMode.PLAIN)

    def teardown_method(self) -> None:
        configure_output(OutputMode.PRETTY)

    def test_print_line_strips_markup(self, capsys: pytest.CaptureFixture[str]) -> None:
        print_line("[bold]Hello[/bold] [cyan]World[/cyan]")
        out = capsys.readouterr().out
        assert out.strip() == "Hello World"
        assert "[bold]" not in out
        assert "[cyan]" not in out

    def test_print_line_no_markup(self, capsys: pytest.CaptureFixture[str]) -> None:
        print_line("plain text")
        assert capsys.readouterr().out.strip() == "plain text"

    def test_print_line_preserves_non_markup_brackets(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Non-Rich brackets like [ERROR] and [Physics] should not be stripped."""
        print_line("[ERROR] NullReferenceException in [Physics]")
        out = capsys.readouterr().out
        assert "[ERROR]" in out
        assert "[Physics]" in out

    def test_print_plain_table(self, capsys: pytest.CaptureFixture[str]) -> None:
        _print_plain_table(
            ["Name", "Value"],
            [["foo", "1"], ["bar", "2"]],
            "My Table",
        )
        out = capsys.readouterr().out
        lines = out.strip().split("\n")
        assert lines[0] == "My Table"
        assert lines[1] == "Name\tValue"
        assert lines[2] == "foo\t1"
        assert lines[3] == "bar\t2"

    def test_print_plain_table_no_title(self, capsys: pytest.CaptureFixture[str]) -> None:
        _print_plain_table(["A", "B"], [["1", "2"]])
        out = capsys.readouterr().out
        lines = out.strip().split("\n")
        assert lines[0] == "A\tB"
        assert lines[1] == "1\t2"

    def test_print_success_plain(self, capsys: pytest.CaptureFixture[str]) -> None:
        print_success("done")
        out = capsys.readouterr().out
        assert "[OK] done" in out
        # No ANSI escapes
        assert "\033" not in out

    def test_print_error_plain(self, capsys: pytest.CaptureFixture[str]) -> None:
        print_error("bad", "E001")
        err = capsys.readouterr().err
        assert "Error: bad" in err
        assert "Code: E001" in err
        assert "\033" not in err

    def test_print_warning_plain(self, capsys: pytest.CaptureFixture[str]) -> None:
        print_warning("caution")
        out = capsys.readouterr().out
        assert "[WARN] caution" in out
        assert "\033" not in out

    def test_print_info_plain(self, capsys: pytest.CaptureFixture[str]) -> None:
        print_info("note")
        out = capsys.readouterr().out
        assert "[INFO] note" in out
        assert "\033" not in out

    def test_print_key_value_plain(self, capsys: pytest.CaptureFixture[str]) -> None:
        print_key_value({"host": "localhost", "port": 6500}, "Config")
        out = capsys.readouterr().out
        assert "Config" in out
        assert "host: localhost" in out
        assert "port: 6500" in out
        assert "[cyan]" not in out

    def test_print_key_value_no_title(self, capsys: pytest.CaptureFixture[str]) -> None:
        print_key_value({"a": "b"})
        out = capsys.readouterr().out
        assert "a: b" in out


# =============================================================================
# Quiet mode
# =============================================================================


class TestQuietMode:
    def setup_method(self) -> None:
        configure_output(OutputMode.PLAIN)
        set_quiet(True)

    def teardown_method(self) -> None:
        set_quiet(False)
        configure_output(OutputMode.PRETTY)

    def test_print_success_suppressed(self, capsys: pytest.CaptureFixture[str]) -> None:
        print_success("should not appear")
        out = capsys.readouterr().out
        assert out == ""

    def test_print_error_not_suppressed(self, capsys: pytest.CaptureFixture[str]) -> None:
        print_error("visible error")
        err = capsys.readouterr().err
        assert "visible error" in err

    def test_print_warning_not_suppressed(self, capsys: pytest.CaptureFixture[str]) -> None:
        print_warning("visible warning")
        out = capsys.readouterr().out
        assert "visible warning" in out

    def test_print_line_not_suppressed(self, capsys: pytest.CaptureFixture[str]) -> None:
        print_line("data output")
        out = capsys.readouterr().out
        assert "data output" in out
