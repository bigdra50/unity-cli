"""CLI E2E tests via CliRunner.

Requires a running Relay Server and Unity Editor (TestProject).
Auto-skipped when the environment is unavailable (via cli_runner fixture).
"""

from __future__ import annotations

from typer.testing import CliRunner

from unity_cli.cli.app import app


class TestExitCodes:
    def test_state_returns_zero(self, cli_runner: CliRunner, cli_args: list[str]) -> None:
        result = cli_runner.invoke(app, [*cli_args, "state"])
        assert result.exit_code == 0

    def test_play_stop_returns_zero(self, cli_runner: CliRunner, cli_args: list[str]) -> None:
        result = cli_runner.invoke(app, [*cli_args, "play"])
        try:
            assert result.exit_code == 0
        finally:
            result = cli_runner.invoke(app, [*cli_args, "stop"])
        assert result.exit_code == 0


class TestQuiet:
    def test_quiet_suppresses_success(self, cli_runner: CliRunner, cli_args: list[str]) -> None:
        result = cli_runner.invoke(app, [*cli_args, "--quiet", "play"])
        try:
            assert "[OK]" not in result.output
        finally:
            cli_runner.invoke(app, [*cli_args, "stop"])

    def test_quiet_preserves_data_output(self, cli_runner: CliRunner, cli_args: list[str]) -> None:
        result = cli_runner.invoke(app, [*cli_args, "--quiet", "state"])
        assert result.exit_code == 0
        # state should still produce data output even in quiet mode
        assert result.output.strip()


class TestVerbose:
    def test_verbose_shows_request_response(self, cli_runner: CliRunner, cli_args: list[str]) -> None:
        result = cli_runner.invoke(app, [*cli_args, "--verbose", "state"])
        assert result.exit_code == 0
        # verbose dumps request/response to stderr.
        # Click <8.2: mix_stderr=True (default) merges stderr into output.
        # Click >=8.2: stderr is always separate.
        combined = result.output + getattr(result, "stderr", "")
        assert ">>>" in combined
        assert "<<<" in combined


class TestConsoleGet:
    def test_stacktrace_flag(self, cli_runner: CliRunner, cli_args: list[str]) -> None:
        result = cli_runner.invoke(app, [*cli_args, "console", "get", "-s"])
        assert result.exit_code == 0

    def test_deprecated_count_warning(self, cli_runner: CliRunner, cli_args: list[str]) -> None:
        result = cli_runner.invoke(app, [*cli_args, "console", "get", "-c", "1"])
        assert result.exit_code == 0
        assert "[WARN]" in result.output

    def test_deprecated_filter_warning(self, cli_runner: CliRunner, cli_args: list[str]) -> None:
        result = cli_runner.invoke(app, [*cli_args, "console", "get", "-f", "x"])
        assert result.exit_code == 0
        assert "[WARN]" in result.output
