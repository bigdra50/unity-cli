"""Shared CLI helper functions."""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any

import typer

from unity_cli.cli.exit_codes import ExitCode, exit_code_for
from unity_cli.cli.output import (
    OutputMode,
    configure_output,
    print_error,
    print_validation_error,
)
from unity_cli.exceptions import UnityCLIError

from .context import CLIContext

# =============================================================================
# Error Handler
# =============================================================================


def _handle_error(e: UnityCLIError) -> None:
    """Print error and raise typer.Exit with the mapped exit code."""
    print_error(e.message, e.code)
    raise typer.Exit(exit_code_for(e)) from None


def handle_cli_errors(fn: Callable[..., None]) -> Callable[..., None]:
    """Decorator that catches UnityCLIError and exits with the mapped code."""

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> None:
        try:
            fn(*args, **kwargs)
        except UnityCLIError as e:
            _handle_error(e)

    return wrapper


def _exit_usage(message: str, usage: str) -> None:
    """Print a validation error and exit with USAGE_ERROR."""
    print_validation_error(message, usage)
    raise typer.Exit(ExitCode.USAGE_ERROR) from None


# =============================================================================
# Per-command JSON helper
# =============================================================================


def _should_json(context: CLIContext, json_flag: bool) -> bool:
    """Return True when output should be JSON.

    Checks per-command --json flag first, then UNITY_CLI_JSON env via context.
    """
    if json_flag:
        configure_output(OutputMode.JSON)
        return True
    return context.output.is_json  # UNITY_CLI_JSON env


# =============================================================================
# Value Parser
# =============================================================================


_JSON_START_CHARS = frozenset('"[{tnf')  # true, null, false, or structured


def _parse_cli_value(raw: str) -> int | float | bool | list[Any] | dict[str, Any] | str | None:
    """Parse a CLI string value into an appropriate Python type.

    Parse order (JSON-first):
      1. json.loads  -- handles true/false, numbers, quoted strings, arrays, objects
      2. Legacy bool -- Python-style "True"/"False" (case-insensitive)
      3. int / float
      4. bare string
    """
    import json

    # Skip json.loads for bare strings that cannot be valid JSON.
    # Valid JSON values start with: digit, '-', '"', '[', '{', 't', 'n', 'f'
    if raw and (raw[0].isdigit() or raw[0] == "-" or raw[0] in _JSON_START_CHARS):
        try:
            parsed: int | float | bool | list[Any] | dict[str, Any] | str | None = json.loads(raw)
            return parsed
        except (ValueError, json.JSONDecodeError):
            pass

    if raw.lower() == "true":
        return True
    if raw.lower() == "false":
        return False

    try:
        return int(raw)
    except ValueError:
        pass

    try:
        return float(raw)
    except ValueError:
        pass

    return raw
