"""CLI exit code tests that do NOT require Relay / Unity.

Uses CliRunner with an unreachable port to verify error exit codes,
and validates usage errors from missing required arguments.
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from unity_cli.cli.app import app
from unity_cli.cli.exit_codes import ExitCode


@pytest.fixture(scope="module")
def runner() -> CliRunner:
    return CliRunner()


class TestConnectionError:
    def test_wrong_port_returns_exit_3(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["--relay-port", "1", "state"])
        assert result.exit_code == ExitCode.CONNECTION_ERROR


class TestUsageError:
    def test_missing_required_arg_gameobject_find(self, runner: CliRunner) -> None:
        """'gameobject find' requires a name argument."""
        result = runner.invoke(app, ["gameobject", "find"])
        assert result.exit_code == ExitCode.USAGE_ERROR
