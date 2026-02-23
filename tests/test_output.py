"""Tests for output module: OutputMode resolution and plain-text helpers."""

from __future__ import annotations

import os
import sys
from unittest.mock import patch

import pytest

from unity_cli.cli.output import (
    OutputConfig,
    OutputMode,
    configure_output,
    print_error,
    print_info,
    print_key_value,
    print_line,
    print_plain_table,
    print_success,
    print_warning,
    resolve_output_mode,
    sanitize_tsv,
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

    def testprint_plain_table(self, capsys: pytest.CaptureFixture[str]) -> None:
        print_plain_table(
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
        print_plain_table(["A", "B"], [["1", "2"]])
        out = capsys.readouterr().out
        lines = out.strip().split("\n")
        assert lines[0] == "A\tB"
        assert lines[1] == "1\t2"

    def test_print_success_plain(self, capsys: pytest.CaptureFixture[str]) -> None:
        print_success("done")
        out = capsys.readouterr().out
        assert out.strip() == "done"
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

    def test_print_key_value_plain_tab_separated(self, capsys: pytest.CaptureFixture[str]) -> None:
        print_key_value({"host": "localhost", "port": 6500}, "Config")
        out = capsys.readouterr().out
        lines = out.strip().split("\n")
        assert lines[0] == "host\tlocalhost"
        assert lines[1] == "port\t6500"
        assert "Config" not in out
        assert "[cyan]" not in out

    def test_print_key_value_plain_no_title(self, capsys: pytest.CaptureFixture[str]) -> None:
        print_key_value({"a": "b"})
        out = capsys.readouterr().out
        assert out.strip() == "a\tb"

    def test_print_key_value_plain_sanitizes_tabs(self, capsys: pytest.CaptureFixture[str]) -> None:
        print_key_value({"key": "val\twith\ttabs"})
        out = capsys.readouterr().out
        assert out.strip() == "key\tval with tabs"


# =============================================================================
# _sanitize_tsv
# =============================================================================


class TestSanitizeTsv:
    def test_replaces_tab_with_space(self) -> None:
        assert sanitize_tsv("a\tb") == "a b"

    def test_replaces_newline_with_space(self) -> None:
        assert sanitize_tsv("line1\nline2") == "line1 line2"

    def test_removes_carriage_return(self) -> None:
        assert sanitize_tsv("text\r\nmore") == "text  more"

    def test_normal_string_unchanged(self) -> None:
        assert sanitize_tsv("hello world") == "hello world"

    def test_empty_string(self) -> None:
        assert sanitize_tsv("") == ""

    def test_multiple_tabs_and_newlines(self) -> None:
        assert sanitize_tsv("a\tb\tc\nd\re") == "a b c d e"

    def test_strips_esc_control_character(self) -> None:
        assert sanitize_tsv("hello\x1b[31mred\x1b[0m") == "hello[31mred[0m"

    def test_strips_null_and_del(self) -> None:
        assert sanitize_tsv("a\x00b\x7fc") == "abc"

    def test_strips_other_c0_controls(self) -> None:
        assert sanitize_tsv("a\x01\x02\x0b\x1fb") == "ab"


# =============================================================================
# _print_plain_table header control
# =============================================================================


class TestPrintPlainTableHeader:
    def setup_method(self) -> None:
        configure_output(OutputMode.PLAIN)

    def teardown_method(self) -> None:
        configure_output(OutputMode.PRETTY)

    def test_header_false_omits_header_row(self, capsys: pytest.CaptureFixture[str]) -> None:
        print_plain_table(["Name", "ID"], [["Cube", "123"], ["Sphere", "456"]], header=False)
        out = capsys.readouterr().out
        lines = out.strip().split("\n")
        assert len(lines) == 2
        assert lines[0] == "Cube\t123"
        assert lines[1] == "Sphere\t456"

    def test_header_true_includes_header_row(self, capsys: pytest.CaptureFixture[str]) -> None:
        print_plain_table(["Name", "ID"], [["Cube", "123"]], header=True)
        out = capsys.readouterr().out
        lines = out.strip().split("\n")
        assert lines[0] == "Name\tID"
        assert lines[1] == "Cube\t123"

    def test_sanitize_tsv_applied_to_rows(self, capsys: pytest.CaptureFixture[str]) -> None:
        print_plain_table(["Col"], [["data\twith\ttabs"], ["line\nbreak"]])
        out = capsys.readouterr().out
        lines = out.strip().split("\n")
        assert lines[1] == "data with tabs"
        assert lines[2] == "line break"


# =============================================================================
# PRETTY mode regression
# =============================================================================


class TestPrettyModeRegression:
    def setup_method(self) -> None:
        configure_output(OutputMode.PRETTY)

    def test_print_key_value_pretty_with_title(self, capsys: pytest.CaptureFixture[str]) -> None:
        print_key_value({"host": "localhost", "port": 6500}, "Config")
        out = capsys.readouterr().out
        assert "Config" in out
        assert "host:" in out
        assert "localhost" in out

    def test_print_key_value_pretty_indented(self, capsys: pytest.CaptureFixture[str]) -> None:
        print_key_value({"a": "b"})
        out = capsys.readouterr().out
        assert "a:" in out
        assert "b" in out


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
