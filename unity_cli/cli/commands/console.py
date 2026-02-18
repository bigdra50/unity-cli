"""Console log commands: get, clear."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from unity_cli.cli.context import CLIContext
from unity_cli.cli.helpers import _handle_error, _should_json
from unity_cli.cli.output import print_json, print_line, print_success, print_warning
from unity_cli.exceptions import UnityCLIError

console_app = typer.Typer(help="Console log commands")


def _parse_level(level: str) -> list[str]:
    """Parse level option like adb logcat style.

    Levels (ascending severity): L (log) < W (warning) < E (error) < X (exception)
    Assert (A) is treated as same level as error.

    Examples:
        "E"   -> ["error", "exception"] (error and above)
        "W"   -> ["warning", "error", "assert", "exception"] (warning and above)
        "+W"  -> ["warning"] (warning only)
        "+E+X" -> ["error", "exception"] (specific types only)
    """
    level = level.upper().strip()

    # Hierarchy mapping (level -> types at that level and above)
    hierarchy = {
        "L": ["log", "warning", "error", "assert", "exception"],
        "W": ["warning", "error", "assert", "exception"],
        "E": ["error", "assert", "exception"],
        "A": ["error", "assert", "exception"],  # Assert same as Error level
        "X": ["exception"],
    }

    # Type mapping for specific selection
    type_map = {
        "L": "log",
        "W": "warning",
        "E": "error",
        "A": "assert",
        "X": "exception",
    }

    # Specific types mode: +E+W or +E
    if level.startswith("+"):
        types = []
        for char in level.replace("+", " ").split():
            if char in type_map:
                types.append(type_map[char])
        return types if types else ["log", "warning", "error", "assert", "exception"]

    # Hierarchy mode: E -> error and above
    if level in hierarchy:
        return hierarchy[level]

    # Invalid level, return all
    return ["log", "warning", "error", "assert", "exception"]


@console_app.command("get")
def console_get(
    ctx: typer.Context,
    level: Annotated[
        str | None,
        typer.Option(
            "--level",
            "-l",
            help="Log level filter: L(log), W(warning), E(error), X(exception). "
            "E.g., '-l W' for warning+, '-l +E' for error only",
        ),
    ] = None,
    count: Annotated[
        int | None,
        typer.Option("--count", "-c", hidden=True, help="[Deprecated] Use: u console get | head -N"),
    ] = None,
    filter_text: Annotated[
        str | None,
        typer.Option("--filter", "-f", hidden=True, help="[Deprecated] Use: u console get | grep PATTERN"),
    ] = None,
    stacktrace: Annotated[
        bool,
        typer.Option("--stacktrace", "-s", help="Include stack traces in output"),
    ] = False,
    verbose_legacy: Annotated[
        bool,
        typer.Option("--verbose", "-v", hidden=True, help="[Deprecated] Use --stacktrace/-s"),
    ] = False,
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Get console logs.

    Level hierarchy: L (log) < W (warning) < E (error) < X (exception)

    Examples:
        u console get              # All logs (plain text)
        u console get --json       # All logs (JSON format)
        u console get -s           # All logs with stack traces
        u console get -l E         # Error and above (error + exception)
        u console get -l W         # Warning and above
        u console get -l +W        # Warning only
        u console get -l +E+X      # Error and exception only
    """
    context: CLIContext = ctx.obj

    include_stacktrace = stacktrace or verbose_legacy
    _warn_deprecated_console_opts(verbose_legacy, count, filter_text)

    try:
        types = _parse_level(level) if level else None
        result = context.client.console.get(
            types=types,
            count=count,
            filter_text=filter_text,
            include_stacktrace=include_stacktrace,
        )

        if _should_json(context, json_flag):
            print_json(result, None)
        else:
            _print_console_entries(result.get("entries", []), include_stacktrace)
    except UnityCLIError as e:
        _handle_error(e)


def _warn_deprecated_console_opts(verbose_legacy: bool, count: int | None, filter_text: str | None) -> None:
    deprecations = [
        (verbose_legacy, "--verbose/-v is deprecated for 'console get'. Use --stacktrace/-s instead."),
        (count is not None, "--count/-c is deprecated. Use: u console get | head -N"),
        (filter_text is not None, "--filter/-f is deprecated. Use: u console get | grep PATTERN"),
    ]
    for cond, msg in deprecations:
        if cond:
            print_warning(msg)


def _print_console_entries(entries: list[dict[str, Any]], include_stacktrace: bool) -> None:
    for entry in entries:
        print_line(f"{entry.get('timestamp', '')} {entry.get('type', 'log')} {entry.get('message', '')}")
        if include_stacktrace and entry.get("stackTrace"):
            for st_line in entry["stackTrace"].split("\n"):
                print_line(f"  {st_line}")


@console_app.command("clear")
def console_clear(ctx: typer.Context) -> None:
    """Clear console logs."""
    context: CLIContext = ctx.obj
    try:
        context.client.console.clear()
        print_success("Console cleared")
    except UnityCLIError as e:
        _handle_error(e)
