"""
Unity CLI - Typer Application
==============================

Main Typer application definition with basic commands
and sub-command groups for scene, tests, gameobject, component, etc.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import version as pkg_version
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.markup import escape

from unity_cli.cli.exit_codes import ExitCode, exit_code_for
from unity_cli.cli.output import (
    OutputConfig,
    OutputMode,
    _print_plain_table,
    configure_output,
    get_console,
    get_err_console,
    is_no_color,
    print_components_table,
    print_error,
    print_hierarchy_table,
    print_info,
    print_instances_table,
    print_json,
    print_key_value,
    print_line,
    print_success,
    print_validation_error,
    print_warning,
    resolve_output_mode,
    set_quiet,
)
from unity_cli.client import UnityClient
from unity_cli.config import CONFIG_FILE_NAME, UnityCLIConfig
from unity_cli.exceptions import UnityCLIError

# =============================================================================
# Error Handler
# =============================================================================


def _handle_error(e: UnityCLIError) -> None:
    """Print error and raise typer.Exit with the mapped exit code."""
    print_error(e.message, e.code)
    raise typer.Exit(exit_code_for(e)) from None


# =============================================================================
# Retry Callback
# =============================================================================


def _on_retry_callback(code: str, message: str, attempt: int, backoff_ms: int) -> None:
    """Callback for retry events - outputs to stderr."""
    import sys

    from unity_cli.cli import output

    if output.err_console.no_color:
        print(
            f"[Retry] {code}: {message} (attempt {attempt}, waiting {backoff_ms}ms)",
            file=sys.stderr,
        )
    else:
        output.get_err_console().print(
            f"[dim][Retry][/dim] {code}: {message} (attempt {attempt}, waiting {backoff_ms}ms)",
            style="yellow",
        )


# =============================================================================
# Context Object
# =============================================================================


@dataclass
class CLIContext:
    """Context object shared across commands via ctx.obj."""

    config: UnityCLIConfig
    client: UnityClient
    output: OutputConfig = OutputConfig(mode=OutputMode.PRETTY)
    quiet: bool = False


# =============================================================================
# Main Application
# =============================================================================

app = typer.Typer(
    name="unity-cli",
    help="Unity CLI - Control Unity Editor via Relay Server",
    no_args_is_help=True,
    rich_markup_mode="rich",
)


# =============================================================================
# Global Options Callback
# =============================================================================


@app.callback()
def main(
    ctx: typer.Context,
    relay_host: Annotated[
        str | None,
        typer.Option(
            "--relay-host",
            help="Relay server host",
            envvar="UNITY_RELAY_HOST",
        ),
    ] = None,
    relay_port: Annotated[
        int | None,
        typer.Option(
            "--relay-port",
            help="Relay server port",
            envvar="UNITY_RELAY_PORT",
        ),
    ] = None,
    instance: Annotated[
        str | None,
        typer.Option(
            "--instance",
            "-i",
            help="Target Unity instance (path, project name, or prefix)",
            envvar="UNITY_INSTANCE",
        ),
    ] = None,
    timeout: Annotated[
        float | None,
        typer.Option(
            "--timeout",
            "-t",
            help="Timeout in seconds",
        ),
    ] = None,
    pretty_flag: Annotated[
        bool | None,
        typer.Option(
            "--pretty/--no-pretty",
            help="Force pretty or plain output",
        ),
    ] = None,
    quiet: Annotated[
        bool,
        typer.Option(
            "--quiet",
            "-q",
            help="Suppress success messages (errors still go to stderr)",
            envvar="UNITY_CLI_QUIET",
        ),
    ] = False,
) -> None:
    """Unity CLI - Control Unity Editor via Relay Server."""
    # Resolve output mode and configure consoles
    output_mode = resolve_output_mode(pretty_flag=pretty_flag)
    configure_output(output_mode)
    output_config = OutputConfig(mode=output_mode)
    set_quiet(quiet)

    # Load config from file
    config = UnityCLIConfig.load()

    # Override with CLI options
    if relay_host is not None:
        config.relay_host = relay_host
    if relay_port is not None:
        config.relay_port = relay_port
    if timeout is not None:
        config.timeout = timeout
    if instance is not None:
        resolved = Path(instance).resolve()
        config.instance = str(resolved) if resolved.is_dir() else instance

    # Create client with retry callback for CLI feedback
    client = UnityClient(
        relay_host=config.relay_host,
        relay_port=config.relay_port,
        timeout=config.timeout,
        instance=config.instance,
        timeout_ms=config.timeout_ms,
        retry_initial_ms=config.retry_initial_ms,
        retry_max_ms=config.retry_max_ms,
        retry_max_time_ms=config.retry_max_time_ms,
        on_retry=_on_retry_callback,
    )

    # Store in context for sub-commands
    ctx.obj = CLIContext(
        config=config,
        client=client,
        output=output_config,
        quiet=quiet,
    )


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
# Basic Commands
# =============================================================================


@app.command()
def version() -> None:
    """Show CLI version."""
    try:
        ver = pkg_version("unity-cli")
    except Exception:
        ver = "unknown"
    print_line(f"unity-cli {ver}")


@app.command()
def instances(
    ctx: typer.Context,
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """List connected Unity instances."""
    context: CLIContext = ctx.obj
    try:
        result = context.client.list_instances()

        if _should_json(context, json_flag):
            print_json(result, None)
        else:
            print_instances_table(result)
    except UnityCLIError as e:
        _handle_error(e)


@app.command()
def state(
    ctx: typer.Context,
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Get editor state."""
    context: CLIContext = ctx.obj
    try:
        result = context.client.editor.get_state()
        if _should_json(context, json_flag):
            print_json(result, None)
        else:
            print_key_value(result, "Editor State")
    except UnityCLIError as e:
        _handle_error(e)


@app.command()
def play(ctx: typer.Context) -> None:
    """Enter play mode."""
    context: CLIContext = ctx.obj
    try:
        context.client.editor.play()
        print_success("Entered play mode")
    except UnityCLIError as e:
        _handle_error(e)


@app.command()
def stop(ctx: typer.Context) -> None:
    """Exit play mode."""
    context: CLIContext = ctx.obj
    try:
        context.client.editor.stop()
        print_success("Exited play mode")
    except UnityCLIError as e:
        _handle_error(e)


@app.command()
def pause(ctx: typer.Context) -> None:
    """Toggle pause."""
    context: CLIContext = ctx.obj
    try:
        context.client.editor.pause()
        print_success("Toggled pause")
    except UnityCLIError as e:
        _handle_error(e)


@app.command()
def refresh(ctx: typer.Context) -> None:
    """Refresh asset database (trigger recompilation)."""
    context: CLIContext = ctx.obj
    try:
        context.client.editor.refresh()
        print_success("Asset database refreshed")
    except UnityCLIError as e:
        _handle_error(e)


# =============================================================================
# Value Parser
# =============================================================================


def _parse_cli_value(raw: str) -> int | float | bool | list[Any] | dict[str, Any] | str:
    """Parse a CLI string value into an appropriate Python type.

    Handles: int, float, bool, JSON array, JSON object, or plain string.
    """
    import json

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

    if raw.startswith(("[", "{")):
        try:
            parsed: list[Any] | dict[str, Any] = json.loads(raw)
            return parsed
        except json.JSONDecodeError:
            pass

    return raw


# =============================================================================
# Console Commands
# =============================================================================

console_app = typer.Typer(help="Console log commands")
app.add_typer(console_app, name="console")


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
        typer.Option("--count", "-c", help="Number of logs to retrieve (default: all)"),
    ] = None,
    filter_text: Annotated[
        str | None,
        typer.Option("--filter", "-f", help="Text to filter logs"),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Include stack traces in output"),
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
        u console get -v           # All logs with stack traces
        u console get -l E         # Error and above (error + exception)
        u console get -l W         # Warning and above
        u console get -l +W        # Warning only
        u console get -l +E+X      # Error and exception only
    """
    context: CLIContext = ctx.obj
    try:
        # Parse level option to types list
        types = _parse_level(level) if level else None
        result = context.client.console.get(
            types=types,
            count=count,
            filter_text=filter_text,
            include_stacktrace=verbose,
        )

        if _should_json(context, json_flag):
            print_json(result, None)
        else:
            # Plain text output: timestamp type message
            entries = result.get("entries", [])
            for entry in entries:
                ts = entry.get("timestamp", "")
                log_type = entry.get("type", "log")
                msg = entry.get("message", "")
                print_line(f"{ts} {log_type} {msg}")
                if verbose and entry.get("stackTrace"):
                    for st_line in entry["stackTrace"].split("\n"):
                        print_line(f"  {st_line}")
    except UnityCLIError as e:
        _handle_error(e)


@console_app.command("clear")
def console_clear(ctx: typer.Context) -> None:
    """Clear console logs."""
    context: CLIContext = ctx.obj
    try:
        context.client.console.clear()
        print_success("Console cleared")
    except UnityCLIError as e:
        _handle_error(e)


# =============================================================================
# Scene Commands
# =============================================================================

scene_app = typer.Typer(help="Scene management commands")
app.add_typer(scene_app, name="scene")


@scene_app.command("active")
def scene_active(
    ctx: typer.Context,
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Get active scene info."""
    context: CLIContext = ctx.obj
    try:
        result = context.client.scene.get_active()
        if _should_json(context, json_flag):
            print_json(result, None)
        else:
            print_key_value(result, "Active Scene")
    except UnityCLIError as e:
        _handle_error(e)


@scene_app.command("hierarchy")
def scene_hierarchy(
    ctx: typer.Context,
    depth: Annotated[int, typer.Option("--depth", "-d", help="Hierarchy depth")] = 1,
    page_size: Annotated[int, typer.Option("--page-size", help="Page size")] = 50,
    cursor: Annotated[int, typer.Option("--cursor", help="Pagination cursor")] = 0,
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Get scene hierarchy."""
    context: CLIContext = ctx.obj
    try:
        result = context.client.scene.get_hierarchy(
            depth=depth,
            page_size=page_size,
            cursor=cursor,
        )
        if _should_json(context, json_flag):
            print_json(result)
        else:
            print_hierarchy_table(result.get("items", []))
    except UnityCLIError as e:
        _handle_error(e)


@scene_app.command("load")
def scene_load(
    ctx: typer.Context,
    path: Annotated[str | None, typer.Option("--path", "-p", help="Scene path")] = None,
    name: Annotated[str | None, typer.Option("--name", "-n", help="Scene name")] = None,
    additive: Annotated[bool, typer.Option("--additive", "-a", help="Load additively")] = False,
) -> None:
    """Load a scene."""
    context: CLIContext = ctx.obj

    if not path and not name:
        print_validation_error("--path or --name required", "u scene load")
        raise typer.Exit(ExitCode.USAGE_ERROR) from None

    try:
        result = context.client.scene.load(path=path, name=name, additive=additive)
        print_success(result.get("message", "Scene loaded"))
    except UnityCLIError as e:
        _handle_error(e)


@scene_app.command("save")
def scene_save(
    ctx: typer.Context,
    path: Annotated[str | None, typer.Option("--path", "-p", help="Save path")] = None,
) -> None:
    """Save current scene."""
    context: CLIContext = ctx.obj
    try:
        result = context.client.scene.save(path=path)
        print_success(result.get("message", "Scene saved"))
    except UnityCLIError as e:
        _handle_error(e)


# =============================================================================
# Tests Commands
# =============================================================================

tests_app = typer.Typer(help="Test execution commands")
app.add_typer(tests_app, name="tests")


def _complete_test_mode(incomplete: str) -> list[tuple[str, str]]:
    """Autocompletion for test mode argument."""
    modes = [
        ("edit", "Run EditMode tests"),
        ("play", "Run PlayMode tests"),
    ]
    return [(m, h) for m, h in modes if m.startswith(incomplete)]


def _poll_test_results(context: CLIContext, interval: float = 1.5) -> dict[str, Any]:
    """Poll test status until completion, showing progress on stderr.

    Args:
        context: CLI context with client
        interval: Polling interval in seconds

    Returns:
        Final test results dict

    Raises:
        typer.Exit: On KeyboardInterrupt (code 130) or test failure (code 1)
    """
    import time

    try:
        if is_no_color():
            # PLAIN/JSON mode: simple stderr polling without Rich Live
            import sys as _sys

            _sys.stderr.write("Waiting for tests...\n")
            while True:
                time.sleep(interval)
                status = context.client.tests.status()

                if status.get("running"):
                    passed = status.get("passed", 0)
                    failed = status.get("failed", 0)
                    skipped = status.get("skipped", 0)
                    started = status.get("testsStarted", 0)
                    finished = status.get("testsFinished", 0)
                    _sys.stderr.write(
                        f"\rRunning tests ({finished}/{started}) Pass:{passed} Fail:{failed} Skip:{skipped}"
                    )
                    _sys.stderr.flush()
                    continue

                _sys.stderr.write("\n")
                return status
        else:
            from rich.live import Live
            from rich.text import Text as RichText

            with Live(
                RichText("Waiting for tests...", style="dim"),
                console=get_err_console(),
                refresh_per_second=2,
            ) as live:
                while True:
                    time.sleep(interval)
                    status = context.client.tests.status()

                    if status.get("running"):
                        passed = status.get("passed", 0)
                        failed = status.get("failed", 0)
                        skipped = status.get("skipped", 0)
                        started = status.get("testsStarted", 0)
                        finished = status.get("testsFinished", 0)

                        progress = RichText()
                        progress.append("Running tests ", style="bold")
                        progress.append(f"({finished}/{started}) ", style="dim")
                        progress.append(f"Pass:{passed}", style="green")
                        progress.append(" ")
                        progress.append(f"Fail:{failed}", style="red" if failed else "dim")
                        progress.append(" ")
                        progress.append(f"Skip:{skipped}", style="yellow" if skipped else "dim")
                        live.update(progress)
                        continue

                    # Test run complete or no active run
                    return status
    except KeyboardInterrupt:
        print_warning("Polling interrupted. Tests may still be running in Unity.")
        print_info("Use 'u tests status' to check progress.")
        raise typer.Exit(130) from None


@tests_app.command("run")
def tests_run(
    ctx: typer.Context,
    mode: Annotated[str, typer.Argument(help="Test mode (edit or play)", autocompletion=_complete_test_mode)] = "edit",
    test_names: Annotated[
        list[str] | None,
        typer.Option("--test-names", "-n", help="Specific test names"),
    ] = None,
    categories: Annotated[
        list[str] | None,
        typer.Option("--categories", "-c", help="Test categories"),
    ] = None,
    assemblies: Annotated[
        list[str] | None,
        typer.Option("--assemblies", "-a", help="Assembly names"),
    ] = None,
    group_pattern: Annotated[
        str | None,
        typer.Option("--group-pattern", "-g", help="Regex pattern for test names"),
    ] = None,
    no_wait: Annotated[
        bool,
        typer.Option("--no-wait", help="Return immediately without waiting for results"),
    ] = False,
) -> None:
    """Run Unity tests."""
    context: CLIContext = ctx.obj
    try:
        result = context.client.tests.run(
            mode=mode,
            test_names=test_names,
            categories=categories,
            assemblies=assemblies,
            group_pattern=group_pattern,
        )

        if no_wait:
            print_success(result.get("message", "Tests started"))
            return

        # Auto-poll for results
        from unity_cli.cli.output import print_test_results_table

        final = _poll_test_results(context)

        if "tests" in final:
            print_test_results_table(final["tests"])
        else:
            print_key_value(final)

        if final.get("failed", 0) > 0:
            raise typer.Exit(ExitCode.USAGE_ERROR)
    except UnityCLIError as e:
        _handle_error(e)


@tests_app.command("list")
def tests_list(
    ctx: typer.Context,
    mode: Annotated[str, typer.Argument(help="Test mode (edit or play)", autocompletion=_complete_test_mode)] = "edit",
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """List available tests."""
    context: CLIContext = ctx.obj
    try:
        result = context.client.tests.list(mode=mode)
        if _should_json(context, json_flag):
            print_json(result, None)
        else:
            tests = result.get("tests", [])
            print_line(f"[bold]Tests ({escape(mode)}Mode): {len(tests)}[/bold]")
            for t in tests:
                print_line(f"  {escape(str(t))}")
    except UnityCLIError as e:
        _handle_error(e)


@tests_app.command("status")
def tests_status(
    ctx: typer.Context,
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Check running test status."""
    context: CLIContext = ctx.obj
    try:
        result = context.client.tests.status()
        if _should_json(context, json_flag):
            print_json(result, None)
        else:
            running = result.get("running", False)
            status_text = "[green]running[/green]" if running else "[dim]idle[/dim]"
            print_line(f"Tests: {status_text}")
            if running:
                passed = result.get("passed", 0)
                failed = result.get("failed", 0)
                skipped = result.get("skipped", 0)
                started = result.get("testsStarted", 0)
                finished = result.get("testsFinished", 0)
                print_line(f"  Progress: {finished}/{started}")
                print_line(f"  Passed: {passed}  Failed: {failed}  Skipped: {skipped}")
    except UnityCLIError as e:
        _handle_error(e)


# =============================================================================
# GameObject Commands
# =============================================================================

gameobject_app = typer.Typer(help="GameObject commands")
app.add_typer(gameobject_app, name="gameobject")


@gameobject_app.command("find")
def gameobject_find(
    ctx: typer.Context,
    name: Annotated[str | None, typer.Option("--name", "-n", help="GameObject name")] = None,
    id: Annotated[int | None, typer.Option("--id", help="Instance ID")] = None,
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Find GameObjects by name or ID."""
    context: CLIContext = ctx.obj

    if not name and id is None:
        print_validation_error("--name or --id required", "u gameobject find")
        raise typer.Exit(ExitCode.USAGE_ERROR) from None

    try:
        result = context.client.gameobject.find(name=name, instance_id=id)
        if _should_json(context, json_flag):
            print_json(result)
        else:
            objects = result.get("objects", [])
            print_line(f"[bold]Found {len(objects)} GameObject(s)[/bold]")
            for obj in objects:
                obj_name = escape(obj.get("name", "Unknown"))
                obj_id = obj.get("instanceID", "")
                print_line(f"  {obj_name} (ID: {obj_id})")
    except UnityCLIError as e:
        _handle_error(e)


@gameobject_app.command("create")
def gameobject_create(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name", "-n", help="GameObject name")],
    primitive: Annotated[
        str | None,
        typer.Option("--primitive", "-p", help="Primitive type (Cube, Sphere, etc.)"),
    ] = None,
    position: Annotated[
        tuple[float, float, float] | None,
        typer.Option("--position", help="Position (X Y Z)"),
    ] = None,
    rotation: Annotated[
        tuple[float, float, float] | None,
        typer.Option("--rotation", help="Rotation (X Y Z)"),
    ] = None,
    scale: Annotated[
        tuple[float, float, float] | None,
        typer.Option("--scale", help="Scale (X Y Z)"),
    ] = None,
) -> None:
    """Create a new GameObject."""
    context: CLIContext = ctx.obj
    try:
        result = context.client.gameobject.create(
            name=name,
            primitive_type=primitive,
            position=list(position) if position else None,
            rotation=list(rotation) if rotation else None,
            scale=list(scale) if scale else None,
        )
        print_success(result.get("message", f"Created: {name}"))
    except UnityCLIError as e:
        _handle_error(e)


@gameobject_app.command("modify")
def gameobject_modify(
    ctx: typer.Context,
    name: Annotated[str | None, typer.Option("--name", "-n", help="GameObject name")] = None,
    id: Annotated[int | None, typer.Option("--id", help="Instance ID")] = None,
    position: Annotated[
        tuple[float, float, float] | None,
        typer.Option("--position", help="Position (X Y Z)"),
    ] = None,
    rotation: Annotated[
        tuple[float, float, float] | None,
        typer.Option("--rotation", help="Rotation (X Y Z)"),
    ] = None,
    scale: Annotated[
        tuple[float, float, float] | None,
        typer.Option("--scale", help="Scale (X Y Z)"),
    ] = None,
) -> None:
    """Modify GameObject transform."""
    context: CLIContext = ctx.obj

    if not name and id is None:
        print_validation_error("--name or --id required", "u gameobject modify")
        raise typer.Exit(ExitCode.USAGE_ERROR) from None

    try:
        result = context.client.gameobject.modify(
            name=name,
            instance_id=id,
            position=list(position) if position else None,
            rotation=list(rotation) if rotation else None,
            scale=list(scale) if scale else None,
        )
        print_success(result.get("message", "Transform modified"))
    except UnityCLIError as e:
        _handle_error(e)


@gameobject_app.command("active")
def gameobject_active(
    ctx: typer.Context,
    name: Annotated[str | None, typer.Option("--name", "-n", help="GameObject name")] = None,
    id: Annotated[int | None, typer.Option("--id", help="Instance ID")] = None,
    active: Annotated[
        bool,
        typer.Option("--active/--no-active", help="Set active (true) or inactive (false)"),
    ] = True,
) -> None:
    """Set GameObject active state."""
    context: CLIContext = ctx.obj

    if not name and id is None:
        print_validation_error("--name or --id required", "u gameobject active")
        raise typer.Exit(ExitCode.USAGE_ERROR) from None

    try:
        result = context.client.gameobject.set_active(
            active=active,
            name=name,
            instance_id=id,
        )
        print_success(result.get("message", f"Active set to {active}"))
    except UnityCLIError as e:
        _handle_error(e)


@gameobject_app.command("delete")
def gameobject_delete(
    ctx: typer.Context,
    name: Annotated[str | None, typer.Option("--name", "-n", help="GameObject name")] = None,
    id: Annotated[int | None, typer.Option("--id", help="Instance ID")] = None,
) -> None:
    """Delete a GameObject."""
    context: CLIContext = ctx.obj

    if not name and id is None:
        print_validation_error("--name or --id required", "u gameobject delete")
        raise typer.Exit(ExitCode.USAGE_ERROR) from None

    try:
        result = context.client.gameobject.delete(name=name, instance_id=id)
        print_success(result.get("message", "GameObject deleted"))
    except UnityCLIError as e:
        _handle_error(e)


# =============================================================================
# Component Commands
# =============================================================================

component_app = typer.Typer(help="Component commands")
app.add_typer(component_app, name="component")


@component_app.command("list")
def component_list(
    ctx: typer.Context,
    target: Annotated[str | None, typer.Option("--target", "-t", help="Target GameObject name")] = None,
    target_id: Annotated[int | None, typer.Option("--target-id", help="Target GameObject ID")] = None,
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """List components on a GameObject."""
    context: CLIContext = ctx.obj

    if not target and target_id is None:
        print_validation_error("--target or --target-id required", "u component list")
        raise typer.Exit(ExitCode.USAGE_ERROR) from None

    try:
        result = context.client.component.list(target=target, target_id=target_id)
        if _should_json(context, json_flag):
            print_json(result)
        else:
            print_components_table(result.get("components", []))
    except UnityCLIError as e:
        _handle_error(e)


@component_app.command("inspect")
def component_inspect(
    ctx: typer.Context,
    component_type: Annotated[str, typer.Option("--type", "-T", help="Component type name")],
    target: Annotated[str | None, typer.Option("--target", "-t", help="Target GameObject name")] = None,
    target_id: Annotated[int | None, typer.Option("--target-id", help="Target GameObject ID")] = None,
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Inspect component properties."""
    context: CLIContext = ctx.obj

    if not target and target_id is None:
        print_validation_error("--target or --target-id required", "u component inspect")
        raise typer.Exit(ExitCode.USAGE_ERROR) from None

    try:
        result = context.client.component.inspect(
            target=target,
            target_id=target_id,
            component_type=component_type,
        )
        if _should_json(context, json_flag):
            print_json(result, None)
        else:
            print_key_value(result, component_type)
    except UnityCLIError as e:
        _handle_error(e)


@component_app.command("add")
def component_add(
    ctx: typer.Context,
    component_type: Annotated[str, typer.Option("--type", "-T", help="Component type name to add")],
    target: Annotated[str | None, typer.Option("--target", "-t", help="Target GameObject name")] = None,
    target_id: Annotated[int | None, typer.Option("--target-id", help="Target GameObject ID")] = None,
) -> None:
    """Add a component to a GameObject."""
    context: CLIContext = ctx.obj

    if not target and target_id is None:
        print_validation_error("--target or --target-id required", "u component add")
        raise typer.Exit(ExitCode.USAGE_ERROR) from None

    try:
        result = context.client.component.add(
            target=target,
            target_id=target_id,
            component_type=component_type,
        )
        print_success(result.get("message", "Component added"))
    except UnityCLIError as e:
        _handle_error(e)


@component_app.command("modify")
def component_modify(
    ctx: typer.Context,
    component_type: Annotated[str, typer.Option("--type", "-T", help="Component type name")],
    prop: Annotated[str, typer.Option("--prop", "-p", help="Property name to modify")],
    value: Annotated[
        str,
        typer.Option("--value", "-v", help="New value (auto-parsed: numbers, booleans, JSON arrays/objects)"),
    ],
    target: Annotated[str | None, typer.Option("--target", "-t", help="Target GameObject name")] = None,
    target_id: Annotated[int | None, typer.Option("--target-id", help="Target GameObject ID")] = None,
) -> None:
    """Modify a component property.

    Values are auto-parsed: integers, floats, booleans (true/false),
    JSON arrays ([1,2,3]), and JSON objects ({"r":1,"g":0,"b":0}) are
    converted to their appropriate types. Everything else is sent as a string.

    Examples:
        u component modify -t "Main Camera" -T Camera --prop fieldOfView --value 90
        u component modify -t "Cube" -T Transform --prop m_LocalPosition --value "[1,2,3]"
    """
    context: CLIContext = ctx.obj

    if not target and target_id is None:
        print_validation_error("--target or --target-id required", "u component modify")
        raise typer.Exit(ExitCode.USAGE_ERROR) from None

    parsed_value = _parse_cli_value(value)

    try:
        result = context.client.component.modify(
            target=target,
            target_id=target_id,
            component_type=component_type,
            prop=prop,
            value=parsed_value,
        )
        print_success(result.get("message", "Property modified"))
    except UnityCLIError as e:
        _handle_error(e)


@component_app.command("remove")
def component_remove(
    ctx: typer.Context,
    component_type: Annotated[str, typer.Option("--type", "-T", help="Component type name to remove")],
    target: Annotated[str | None, typer.Option("--target", "-t", help="Target GameObject name")] = None,
    target_id: Annotated[int | None, typer.Option("--target-id", help="Target GameObject ID")] = None,
) -> None:
    """Remove a component from a GameObject."""
    context: CLIContext = ctx.obj

    if not target and target_id is None:
        print_validation_error("--target or --target-id required", "u component remove")
        raise typer.Exit(ExitCode.USAGE_ERROR) from None

    try:
        result = context.client.component.remove(
            target=target,
            target_id=target_id,
            component_type=component_type,
        )
        print_success(result.get("message", "Component removed"))
    except UnityCLIError as e:
        _handle_error(e)


# =============================================================================
# Menu Commands
# =============================================================================

menu_app = typer.Typer(help="Menu item commands")
app.add_typer(menu_app, name="menu")


@menu_app.command("exec")
def menu_exec(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Menu item path (e.g., 'Edit/Play')")],
) -> None:
    """Execute a Unity menu item."""
    context: CLIContext = ctx.obj
    try:
        result = context.client.menu.execute(path)
        if result.get("success"):
            print_success(result.get("message", f"Executed: {path}"))
        else:
            print_error(result.get("message", f"Failed: {path}"))
            raise typer.Exit(ExitCode.INSTANCE_ERROR) from None
    except UnityCLIError as e:
        _handle_error(e)


@menu_app.command("list")
def menu_list(
    ctx: typer.Context,
    filter_text: Annotated[
        str | None,
        typer.Option("--filter", "-f", help="Filter menu items (case-insensitive)"),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", help="Maximum items to return"),
    ] = 100,
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """List available menu items."""
    context: CLIContext = ctx.obj
    try:
        result = context.client.menu.list(filter_text=filter_text, limit=limit)
        if _should_json(context, json_flag):
            print_json(result)
        else:
            items = result.get("items", [])
            print_line(f"[bold]Menu Items ({len(items)})[/bold]")
            for item in items:
                print_line(f"  {escape(str(item))}")
    except UnityCLIError as e:
        _handle_error(e)


@menu_app.command("context")
def menu_context(
    ctx: typer.Context,
    method: Annotated[str, typer.Argument(help="ContextMenu method name")],
    target: Annotated[
        str | None,
        typer.Option("--target", "-t", help="Target object path (hierarchy or asset)"),
    ] = None,
) -> None:
    """Execute a ContextMenu method on target object."""
    context: CLIContext = ctx.obj
    try:
        result = context.client.menu.context(method=method, target=target)
        print_success(result.get("message", f"Executed: {method}"))
    except UnityCLIError as e:
        _handle_error(e)


# =============================================================================
# Asset Commands
# =============================================================================

asset_app = typer.Typer(help="Asset commands (Prefab, ScriptableObject)")
app.add_typer(asset_app, name="asset")


@asset_app.command("prefab")
def asset_prefab(
    ctx: typer.Context,
    path: Annotated[str, typer.Option("--path", "-p", help="Output path (e.g., Assets/Prefabs/My.prefab)")],
    source: Annotated[str | None, typer.Option("--source", "-s", help="Source GameObject name")] = None,
    source_id: Annotated[int | None, typer.Option("--source-id", help="Source GameObject instance ID")] = None,
) -> None:
    """Create a Prefab from a GameObject."""
    context: CLIContext = ctx.obj

    if not source and source_id is None:
        print_validation_error("--source or --source-id required", "u asset prefab")
        raise typer.Exit(ExitCode.USAGE_ERROR) from None

    try:
        result = context.client.asset.create_prefab(
            path=path,
            source=source,
            source_id=source_id,
        )
        print_success(result.get("message", f"Prefab created: {path}"))
    except UnityCLIError as e:
        _handle_error(e)


@asset_app.command("scriptable-object")
def asset_scriptable_object(
    ctx: typer.Context,
    type_name: Annotated[str, typer.Option("--type", "-T", help="ScriptableObject type name")],
    path: Annotated[str, typer.Option("--path", "-p", help="Output path (e.g., Assets/Data/My.asset)")],
) -> None:
    """Create a ScriptableObject asset."""
    context: CLIContext = ctx.obj
    try:
        result = context.client.asset.create_scriptable_object(
            type_name=type_name,
            path=path,
        )
        print_success(result.get("message", f"ScriptableObject created: {path}"))
    except UnityCLIError as e:
        _handle_error(e)


@asset_app.command("info")
def asset_info(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Asset path")],
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Get asset information."""
    context: CLIContext = ctx.obj
    try:
        result = context.client.asset.info(path=path)
        if _should_json(context, json_flag):
            print_json(result, None)
        else:
            print_key_value(result, path)
    except UnityCLIError as e:
        _handle_error(e)


@asset_app.command("deps")
def asset_deps(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Asset path")],
    recursive: Annotated[
        bool,
        typer.Option("--recursive/--no-recursive", "-r/-R", help="Include indirect dependencies"),
    ] = True,
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Get asset dependencies (what this asset depends on)."""
    context: CLIContext = ctx.obj
    try:
        result = context.client.asset.deps(path=path, recursive=recursive)
        if _should_json(context, json_flag):
            print_json(result)
        else:
            deps = result.get("dependencies", [])
            count = result.get("count", len(deps))
            print_line(f"[bold]Dependencies for {path}[/bold] ({count})")
            if result.get("recursive"):
                print_line("[dim](recursive)[/dim]")
            print_line("")
            for dep in deps:
                print_line(f"  {dep.get('path')}")
                print_line(f"    [dim]type: {dep.get('type')}[/dim]")
    except UnityCLIError as e:
        _handle_error(e)


@asset_app.command("refs")
def asset_refs(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Asset path")],
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Get asset referencers (what depends on this asset)."""
    context: CLIContext = ctx.obj
    try:
        result = context.client.asset.refs(path=path)
        if _should_json(context, json_flag):
            print_json(result)
        else:
            refs = result.get("referencers", [])
            count = result.get("count", len(refs))
            print_line(f"[bold]Referencers of {path}[/bold] ({count})")
            print_line("")
            if count == 0:
                print_line("[dim]No references found[/dim]")
            else:
                for ref in refs:
                    print_line(f"  {ref.get('path')}")
                    print_line(f"    [dim]type: {ref.get('type')}[/dim]")
    except UnityCLIError as e:
        _handle_error(e)


# =============================================================================
# Build Commands
# =============================================================================

build_app = typer.Typer(help="Build pipeline commands")
app.add_typer(build_app, name="build")


@build_app.command("settings")
def build_settings(
    ctx: typer.Context,
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Show current build settings."""
    context: CLIContext = ctx.obj
    try:
        result = context.client.build.settings()
        if _should_json(context, json_flag):
            print_json(result)
        else:
            rows_data = [
                ("Target", result.get("target", "")),
                ("Target Group", result.get("targetGroup", "")),
                ("Product Name", result.get("productName", "")),
                ("Company Name", result.get("companyName", "")),
                ("Bundle Version", result.get("bundleVersion", "")),
                ("Scripting Backend", result.get("scriptingBackend", "")),
            ]
            scenes = result.get("scenes", [])
            rows_data.append(("Scenes", str(len(scenes))))

            if is_no_color():
                _print_plain_table(["Key", "Value"], [list(r) for r in rows_data], "Build Settings")
            else:
                from rich.table import Table

                table = Table(title="Build Settings")
                table.add_column("Key", style="cyan")
                table.add_column("Value")
                for k, v in rows_data:
                    table.add_row(k, v)
                get_console().print(table)

            if scenes:
                print_line("")
                for i, s in enumerate(scenes):
                    print_line(f"  {i}: {s}")
    except UnityCLIError as e:
        _handle_error(e)


@build_app.command("run")
def build_run(
    ctx: typer.Context,
    target: Annotated[
        str | None,
        typer.Option("--target", "-t", help="BuildTarget (e.g., StandaloneWindows64, Android, WebGL)"),
    ] = None,
    output: Annotated[
        str | None,
        typer.Option("--output", "-o", help="Output path"),
    ] = None,
    scenes: Annotated[
        list[str] | None,
        typer.Option("--scene", "-s", help="Scene paths to include (repeatable)"),
    ] = None,
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Run a build."""
    context: CLIContext = ctx.obj
    try:
        result = context.client.build.build(
            target=target,
            output_path=output,
            scenes=scenes,
        )
        if _should_json(context, json_flag):
            print_json(result)
        else:
            build_result = result.get("result", "Unknown")
            if build_result == "Succeeded":
                print_success(f"Build succeeded: {result.get('outputPath', '')}")
            else:
                print_error(f"Build {build_result}", "BUILD_FAILED")

            total_time = result.get("totalTime", 0)
            total_size = result.get("totalSize", 0)
            print_line(f"  Time: {total_time:.1f}s")
            print_line(f"  Size: {total_size} bytes")
            print_line(f"  Target: {result.get('target', '')}")
            print_line(f"  Errors: {result.get('totalErrors', 0)}")
            print_line(f"  Warnings: {result.get('totalWarnings', 0)}")

            messages = result.get("messages", [])
            if messages:
                print_line("")
                for msg in messages:
                    msg_type = escape(str(msg.get("type", "")))
                    msg_content = escape(str(msg.get("content", "")))
                    style = "red" if msg.get("type") == "Error" else "yellow"
                    print_line(f"  [{style}]{msg_type}: {msg_content}[/{style}]")

            if build_result != "Succeeded":
                raise typer.Exit(ExitCode.INSTANCE_ERROR) from None
    except UnityCLIError as e:
        _handle_error(e)


@build_app.command("scenes")
def build_scenes(
    ctx: typer.Context,
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """List build scenes."""
    context: CLIContext = ctx.obj
    try:
        result = context.client.build.scenes()
        if _should_json(context, json_flag):
            print_json(result)
        else:
            scenes_list = result.get("scenes", [])

            if is_no_color():
                rows = []
                for i, s in enumerate(scenes_list):
                    enabled = "yes" if s.get("enabled") else "no"
                    rows.append([str(i), s.get("path", ""), enabled, s.get("guid", "")])
                _print_plain_table(["#", "Path", "Enabled", "GUID"], rows, f"Build Scenes ({len(scenes_list)})")
            else:
                from rich.table import Table

                table = Table(title=f"Build Scenes ({len(scenes_list)})")
                table.add_column("#", style="dim", width=3)
                table.add_column("Path", style="cyan")
                table.add_column("Enabled")
                table.add_column("GUID", style="dim")
                for i, s in enumerate(scenes_list):
                    enabled = "[green]yes[/green]" if s.get("enabled") else "[red]no[/red]"
                    table.add_row(str(i), s.get("path", ""), enabled, s.get("guid", ""))
                get_console().print(table)
    except UnityCLIError as e:
        _handle_error(e)


# =============================================================================
# Package Commands (via Relay)
# =============================================================================

package_app = typer.Typer(help="Package Manager commands (via Relay)")
app.add_typer(package_app, name="package")


@package_app.command("list")
def package_list(
    ctx: typer.Context,
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """List installed packages."""
    context: CLIContext = ctx.obj
    try:
        result = context.client.package.list()
        if _should_json(context, json_flag):
            print_json(result)
        else:
            packages = result.get("packages", [])

            if is_no_color():
                rows = [
                    [pkg.get("name", ""), pkg.get("version", ""), pkg.get("displayName", ""), pkg.get("source", "")]
                    for pkg in packages
                ]
                _print_plain_table(["Name", "Version", "Display Name", "Source"], rows, f"Packages ({len(packages)})")
            else:
                from rich.table import Table

                table = Table(title=f"Packages ({len(packages)})")
                table.add_column("Name", style="cyan")
                table.add_column("Version")
                table.add_column("Display Name")
                table.add_column("Source")
                for pkg in packages:
                    table.add_row(
                        pkg.get("name", ""),
                        pkg.get("version", ""),
                        pkg.get("displayName", ""),
                        pkg.get("source", ""),
                    )
                get_console().print(table)
    except UnityCLIError as e:
        _handle_error(e)


@package_app.command("add")
def package_add(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Package ID (e.g., com.unity.textmeshpro@3.0.6)")],
) -> None:
    """Add a package."""
    context: CLIContext = ctx.obj
    try:
        result = context.client.package.add(name)
        print_success(result.get("message", f"Package added: {name}"))
    except UnityCLIError as e:
        _handle_error(e)


@package_app.command("remove")
def package_remove(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Package name (e.g., com.unity.textmeshpro)")],
) -> None:
    """Remove a package."""
    context: CLIContext = ctx.obj
    try:
        result = context.client.package.remove(name)
        print_success(result.get("message", f"Package removed: {name}"))
    except UnityCLIError as e:
        _handle_error(e)


# =============================================================================
# Profiler Commands
# =============================================================================

profiler_app = typer.Typer(help="Profiler commands")
app.add_typer(profiler_app, name="profiler")


@profiler_app.command("status")
def profiler_status(
    ctx: typer.Context,
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Get profiler status."""
    context: CLIContext = ctx.obj
    try:
        result = context.client.profiler.status()
        if _should_json(context, json_flag):
            print_json(result)
        else:
            enabled = result.get("enabled", False)
            status_text = "[green]running[/green]" if enabled else "[dim]stopped[/dim]"
            print_line(f"Profiler: {status_text}")
            print_line(f"Frame range: {result.get('firstFrameIndex', -1)} - {result.get('lastFrameIndex', -1)}")
    except UnityCLIError as e:
        _handle_error(e)


@profiler_app.command("start")
def profiler_start(ctx: typer.Context) -> None:
    """Start profiling."""
    context: CLIContext = ctx.obj
    try:
        result = context.client.profiler.start()
        print_success(result.get("message", "Profiler started"))
        warning = result.get("warning")
        if warning:
            print_warning(warning)
    except UnityCLIError as e:
        _handle_error(e)


@profiler_app.command("stop")
def profiler_stop(ctx: typer.Context) -> None:
    """Stop profiling."""
    context: CLIContext = ctx.obj
    try:
        result = context.client.profiler.stop()
        print_success(result.get("message", "Profiler stopped"))
    except UnityCLIError as e:
        _handle_error(e)


@profiler_app.command("snapshot")
def profiler_snapshot(
    ctx: typer.Context,
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Get current frame profiler data."""
    context: CLIContext = ctx.obj
    try:
        result = context.client.profiler.snapshot()
        if _should_json(context, json_flag):
            print_json(result)
        else:
            display_keys = [
                ("fps", "FPS"),
                ("cpuFrameTimeMs", "CPU Frame Time"),
                ("cpuRenderThreadTimeMs", "CPU Render Thread"),
                ("gpuFrameTimeMs", "GPU Frame Time"),
                ("batches", "Batches"),
                ("drawCalls", "Draw Calls"),
                ("triangles", "Triangles"),
                ("vertices", "Vertices"),
                ("setPassCalls", "SetPass Calls"),
                ("gcAllocCount", "GC Alloc Count"),
                ("gcAllocBytes", "GC Alloc Bytes"),
            ]

            rows = [[label, str(result.get(key))] for key, label in display_keys if result.get(key) is not None]

            if is_no_color():
                _print_plain_table(["Metric", "Value"], rows, f"Frame {result.get('frameIndex', '?')}")
            else:
                from rich.table import Table

                table = Table(title=f"Frame {result.get('frameIndex', '?')}")
                table.add_column("Metric")
                table.add_column("Value", justify="right")
                for r in rows:
                    table.add_row(*r)
                get_console().print(table)
    except UnityCLIError as e:
        _handle_error(e)


@profiler_app.command("frames")
def profiler_frames(
    ctx: typer.Context,
    count: Annotated[
        int,
        typer.Option("--count", "-c", help="Number of frames to retrieve"),
    ] = 10,
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Get recent N frames summary."""
    context: CLIContext = ctx.obj
    try:
        result = context.client.profiler.frames(count=count)
        if _should_json(context, json_flag):
            print_json(result)
        else:
            frames = result.get("frames", [])
            if not frames:
                print_line("[dim]No profiler frames available[/dim]")
                return

            title = f"Profiler Frames ({result.get('firstFrameIndex', '?')}-{result.get('lastFrameIndex', '?')})"
            headers = ["Frame", "FPS", "CPU (ms)", "GPU (ms)", "Batches", "Draw Calls", "GC Alloc"]
            rows = [
                [
                    str(f.get("frameIndex", "")),
                    str(f.get("fps", "-")),
                    str(f.get("cpuFrameTimeMs", "-")),
                    str(f.get("gpuFrameTimeMs", "-")),
                    str(f.get("batches", "-")),
                    str(f.get("drawCalls", "-")),
                    str(f.get("gcAllocBytes", "-")),
                ]
                for f in frames
            ]

            if is_no_color():
                _print_plain_table(headers, rows, title)
            else:
                from rich.table import Table

                table = Table(title=title)
                for h in headers:
                    table.add_column(h, justify="right")
                for r in rows:
                    table.add_row(*r)
                get_console().print(table)
    except UnityCLIError as e:
        _handle_error(e)


# =============================================================================
# UI Tree Commands
# =============================================================================

uitree_app = typer.Typer(help="UI Toolkit tree commands")
app.add_typer(uitree_app, name="uitree")


@uitree_app.command("dump")
def uitree_dump(
    ctx: typer.Context,
    panel: Annotated[
        str | None,
        typer.Option("--panel", "-p", help="Panel name (omit to list panels)"),
    ] = None,
    depth: Annotated[
        int,
        typer.Option("--depth", "-d", help="Max tree depth (-1 = unlimited)"),
    ] = -1,
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Dump UI tree or list panels.

    Examples:
        u uitree dump                              # List panels
        u uitree dump -p "GameView"                # Dump tree as text
        u uitree dump -p "GameView" --json         # Dump tree as JSON
        u uitree dump -p "GameView" -d 3           # Limit depth
    """
    context: CLIContext = ctx.obj
    try:
        server_format = "json" if json_flag or context.output.is_json else "text"
        result = context.client.uitree.dump(
            panel=panel,
            depth=depth,
            format=server_format,
        )

        if _should_json(context, json_flag):
            print_json(result, None)
        elif panel:
            # Tree output for a specific panel
            panel_name = result.get("panel", panel)
            element_count = result.get("elementCount", 0)
            print_line(f"Panel: {panel_name} ({element_count} elements)\n")

            tree_text = result.get("tree", "")
            if tree_text:
                print_line(tree_text)
        else:
            # Panel list
            panels = result.get("panels", [])
            if not panels:
                print_line("[dim]No panels found[/dim]")
                return

            print_line("Panels:")
            for p in panels:
                ctx_type = p.get("contextType", "")
                p_name = p.get("name", "")
                p_count = p.get("elementCount", 0)
                print_line(f"  [{ctx_type}] {p_name} ({p_count} elements)")

    except UnityCLIError as e:
        _handle_error(e)


@uitree_app.command("query")
def uitree_query(
    ctx: typer.Context,
    panel: Annotated[
        str,
        typer.Option("--panel", "-p", help="Panel name"),
    ],
    type_filter: Annotated[
        str | None,
        typer.Option("--type", "-t", help="Element type filter"),
    ] = None,
    name_filter: Annotated[
        str | None,
        typer.Option("--name", "-n", help="Element name filter"),
    ] = None,
    class_filter: Annotated[
        str | None,
        typer.Option("--class", "-c", help="USS class filter"),
    ] = None,
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Query UI elements by type, name, or class.

    Filters are combined as AND conditions.

    Examples:
        u uitree query -p "GameView" -t Button
        u uitree query -p "GameView" -n "StartBtn"
        u uitree query -p "GameView" -c "primary-button"
        u uitree query -p "GameView" -t Button -c "primary-button"
    """
    context: CLIContext = ctx.obj
    try:
        result = context.client.uitree.query(
            panel=panel,
            type=type_filter,
            name=name_filter,
            class_name=class_filter,
        )

        if _should_json(context, json_flag):
            print_json(result, None)
        else:
            matches = result.get("matches", [])
            count = result.get("count", len(matches))
            print_line(f'Found {count} elements in "{panel}":\n')

            if not matches:
                print_line("[dim]No matching elements[/dim]")
                return

            for elem in matches:
                ref = elem.get("ref", "")
                type_name = elem.get("type", "VisualElement")
                elem_name = elem.get("name", "")
                classes = elem.get("classes", [])

                parts = [f"  {ref}", type_name]
                if elem_name:
                    parts.append(f'"{elem_name}"')
                for cls in classes:
                    parts.append(f".{cls}")
                print_line(" ".join(parts))

                path = elem.get("path", "")
                if path:
                    print_line(f"    [dim]path: {path}[/dim]")

                layout = elem.get("layout")
                if layout:
                    x = layout.get("x", 0)
                    y = layout.get("y", 0)
                    w = layout.get("width", 0)
                    h = layout.get("height", 0)
                    print_line(f"    [dim]layout: ({x}, {y}, {w}x{h})[/dim]")

                print_line("")

    except UnityCLIError as e:
        _handle_error(e)


@uitree_app.command("inspect")
def uitree_inspect(
    ctx: typer.Context,
    ref: Annotated[
        str | None,
        typer.Argument(help="Element reference ID (e.g., ref_3)"),
    ] = None,
    panel: Annotated[
        str | None,
        typer.Option("--panel", "-p", help="Panel name"),
    ] = None,
    name: Annotated[
        str | None,
        typer.Option("--name", "-n", help="Element name"),
    ] = None,
    style: Annotated[
        bool,
        typer.Option("--style", "-s", help="Include resolvedStyle"),
    ] = False,
    children: Annotated[
        bool,
        typer.Option("--children", help="Include children info"),
    ] = False,
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Inspect a specific UI element.

    Specify element by ref ID or by panel + name.

    Examples:
        u uitree inspect ref_3
        u uitree inspect -p "GameView" -n "StartBtn"
        u uitree inspect ref_3 --style
        u uitree inspect ref_3 --children
    """
    context: CLIContext = ctx.obj

    if not ref and not (panel and name):
        print_validation_error("ref argument or --panel + --name required", "u uitree inspect")
        raise typer.Exit(ExitCode.USAGE_ERROR) from None

    try:
        result = context.client.uitree.inspect(
            ref=ref,
            panel=panel,
            name=name,
            include_style=style,
            include_children=children,
        )

        if _should_json(context, json_flag):
            print_json(result, None)
        else:
            elem = result

            # Header: ref Type "name"
            elem_ref = elem.get("ref", "")
            elem_type = elem.get("type", "VisualElement")
            elem_name = elem.get("name", "")
            header_parts = []
            if elem_ref:
                header_parts.append(elem_ref)
            header_parts.append(elem_type)
            if elem_name:
                header_parts.append(f'"{elem_name}"')
            print_line(" ".join(header_parts))

            # Classes
            classes = elem.get("classes", [])
            if classes:
                print_line(f"  classes: {' '.join('.' + c for c in classes)}")

            # Properties
            if "visible" in elem:
                print_line(f"  visible: {elem['visible']}")
            if "enabledSelf" in elem:
                hierarchy = elem.get("enabledInHierarchy")
                if hierarchy is not None:
                    print_line(f"  enabled: {elem['enabledSelf']} (hierarchy: {hierarchy})")
                else:
                    print_line(f"  enabled: {elem['enabledSelf']}")
            if "focusable" in elem:
                print_line(f"  focusable: {elem['focusable']}")

            # Layout
            layout = elem.get("layout")
            if layout:
                x = layout.get("x", 0)
                y = layout.get("y", 0)
                w = layout.get("width", 0)
                h = layout.get("height", 0)
                print_line(f"  layout: ({x}, {y}, {w}x{h})")

            # WorldBound
            world_bound = elem.get("worldBound")
            if world_bound:
                x = world_bound.get("x", 0)
                y = world_bound.get("y", 0)
                w = world_bound.get("width", 0)
                h = world_bound.get("height", 0)
                print_line(f"  worldBound: ({x}, {y}, {w}x{h})")

            # Child count
            child_count = elem.get("childCount")
            if child_count is not None:
                print_line(f"  childCount: {child_count}")

            # Path
            path = elem.get("path", "")
            if path:
                print_line(f"  path: {path}")

            # Style section
            style_data = elem.get("resolvedStyle")
            if style_data and isinstance(style_data, dict):
                print_line("\n  resolvedStyle:")
                for k, v in style_data.items():
                    print_line(f"  {k}: {v}")

            # Children section
            children_data = elem.get("children")
            if children_data and isinstance(children_data, list):
                print_line("\n  children:")
                for child in children_data:
                    child_ref = child.get("ref", "")
                    child_type = child.get("type", "VisualElement")
                    child_name = child.get("name", "")
                    parts = ["  " + child_ref, child_type]
                    if child_name:
                        parts.append(f'"{child_name}"')
                    print_line(" ".join(parts))

    except UnityCLIError as e:
        _handle_error(e)


@uitree_app.command("click")
def uitree_click(
    ctx: typer.Context,
    ref: Annotated[
        str | None,
        typer.Argument(help="Element reference ID (e.g., ref_3)"),
    ] = None,
    panel: Annotated[
        str | None,
        typer.Option("--panel", "-p", help="Panel name"),
    ] = None,
    name: Annotated[
        str | None,
        typer.Option("--name", "-n", help="Element name"),
    ] = None,
    button: Annotated[
        int,
        typer.Option("--button", "-b", help="Mouse button (0=left, 1=right, 2=middle)"),
    ] = 0,
    count: Annotated[
        int,
        typer.Option("--count", "-c", help="Click count (2=double click)"),
    ] = 1,
) -> None:
    """Click a UI element.

    Specify element by ref ID or by panel + name.

    Examples:
        u uitree click ref_3                          # Left click
        u uitree click ref_3 --button 1               # Right click
        u uitree click ref_3 --count 2                # Double click
        u uitree click -p "GameView" -n "StartBtn"    # By panel + name
    """
    context: CLIContext = ctx.obj

    if not ref and not (panel and name):
        print_validation_error("ref argument or --panel + --name required", "u uitree click")
        raise typer.Exit(ExitCode.USAGE_ERROR) from None

    if button not in (0, 1, 2):
        print_validation_error("--button must be 0 (left), 1 (right), or 2 (middle)", "u uitree click")
        raise typer.Exit(ExitCode.USAGE_ERROR) from None

    if count < 1:
        print_validation_error("--count must be a positive integer (>= 1)", "u uitree click")
        raise typer.Exit(ExitCode.USAGE_ERROR) from None

    try:
        result = context.client.uitree.click(
            ref=ref,
            panel=panel,
            name=name,
            button=button,
            click_count=count,
        )

        elem_ref = result.get("ref", "")
        elem_type = escape(result.get("type", ""))
        msg = escape(result.get("message", ""))
        print_line(f"{elem_ref} {elem_type}: {msg}")

    except UnityCLIError as e:
        _handle_error(e)


@uitree_app.command("scroll")
def uitree_scroll(
    ctx: typer.Context,
    ref: Annotated[
        str | None,
        typer.Argument(help="Element reference ID (e.g., ref_5)"),
    ] = None,
    panel: Annotated[
        str | None,
        typer.Option("--panel", "-p", help="Panel name"),
    ] = None,
    name: Annotated[
        str | None,
        typer.Option("--name", "-n", help="Element name"),
    ] = None,
    x: Annotated[
        float | None,
        typer.Option("--x", help="Scroll offset X (absolute)"),
    ] = None,
    y: Annotated[
        float | None,
        typer.Option("--y", help="Scroll offset Y (absolute)"),
    ] = None,
    to: Annotated[
        str | None,
        typer.Option("--to", help="Ref ID of child element to scroll into view"),
    ] = None,
) -> None:
    """Scroll a ScrollView element.

    Two modes:
      Offset mode: --x and/or --y to set absolute scroll position.
      ScrollTo mode: --to <ref_id> to scroll a child element into view.

    Examples:
        u uitree scroll ref_5 --y 0                   # Scroll to top
        u uitree scroll ref_5 --y 500                  # Scroll to y=500
        u uitree scroll ref_5 --to ref_12              # Scroll child into view
    """
    context: CLIContext = ctx.obj

    if not ref and not (panel and name):
        print_validation_error("ref argument or --panel + --name required", "u uitree scroll")
        raise typer.Exit(ExitCode.USAGE_ERROR) from None

    if to is None and x is None and y is None:
        print_validation_error("--x/--y or --to parameter required", "u uitree scroll")
        raise typer.Exit(ExitCode.USAGE_ERROR) from None

    try:
        result = context.client.uitree.scroll(
            ref=ref,
            panel=panel,
            name=name,
            x=x,
            y=y,
            to_child=to,
        )

        elem_ref = escape(result.get("ref", ""))
        offset = result.get("scrollOffset", {})
        ox = offset.get("x", 0)
        oy = offset.get("y", 0)
        print_line(f"{elem_ref} ScrollView: scrollOffset=({ox}, {oy})")

    except UnityCLIError as e:
        _handle_error(e)


@uitree_app.command("text")
def uitree_text(
    ctx: typer.Context,
    ref: Annotated[
        str | None,
        typer.Argument(help="Element reference ID (e.g., ref_7)"),
    ] = None,
    panel: Annotated[
        str | None,
        typer.Option("--panel", "-p", help="Panel name"),
    ] = None,
    name: Annotated[
        str | None,
        typer.Option("--name", "-n", help="Element name"),
    ] = None,
) -> None:
    """Get text content of a UI element.

    Specify element by ref ID or by panel + name.

    Examples:
        u uitree text ref_7                           # Get text by ref
        u uitree text -p "GameView" -n "TitleLabel"   # By panel + name
    """
    context: CLIContext = ctx.obj

    if not ref and not (panel and name):
        print_validation_error("ref argument or --panel + --name required", "u uitree text")
        raise typer.Exit(ExitCode.USAGE_ERROR) from None

    try:
        result = context.client.uitree.text(
            ref=ref,
            panel=panel,
            name=name,
        )

        elem_ref = result.get("ref", "")
        elem_type = escape(result.get("type", ""))
        text = escape(result.get("text", ""))
        print_line(f"{elem_ref} {elem_type}: {text}")

    except UnityCLIError as e:
        _handle_error(e)


# =============================================================================
# Config Commands
# =============================================================================

config_app = typer.Typer(help="Configuration commands")
app.add_typer(config_app, name="config")


@config_app.command("show")
def config_show(
    ctx: typer.Context,
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Show current configuration."""
    context: CLIContext = ctx.obj
    config_file = UnityCLIConfig._find_config_file()

    if _should_json(context, json_flag):
        # JSON mode
        data = {
            "config_file": str(config_file) if config_file else None,
            "relay_host": context.config.relay_host,
            "relay_port": context.config.relay_port,
            "timeout": context.config.timeout,
            "instance": context.config.instance,
        }
        print_json(data, None)
    else:
        print_line("[bold]=== Unity CLI Configuration ===[/bold]")
        print_line(f"Config file: {config_file or '[dim]Not found (using defaults)[/dim]'}")
        print_line(f"Relay host: {context.config.relay_host}")
        print_line(f"Relay port: {context.config.relay_port}")
        print_line(f"Timeout: {context.config.timeout}s")
        print_line(f"Instance: {context.config.instance or '[dim](default)[/dim]'}")


@config_app.command("init")
def config_init(
    ctx: typer.Context,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output path"),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite existing config"),
    ] = False,
) -> None:
    """Generate default .unity-cli.toml configuration file."""
    output_path = output or Path(CONFIG_FILE_NAME)

    if output_path.exists() and not force:
        print_error(f"{output_path} already exists. Use --force to overwrite.")
        raise typer.Exit(ExitCode.USAGE_ERROR) from None

    default_config = UnityCLIConfig()
    output_path.write_text(default_config.to_toml())
    print_success(f"Created {output_path}")


# =============================================================================
# Project Commands (file-based, no Relay required)
# =============================================================================

project_app = typer.Typer(help="Project information (file-based, no Relay required)")
app.add_typer(project_app, name="project")


@project_app.command("info")
def project_info(
    ctx: typer.Context,
    path: Annotated[
        Path,
        typer.Argument(help="Unity project path"),
    ] = Path("."),
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Show project information parsed from files.

    Displays: Unity version, product name, company, build scenes, packages.
    No Relay Server connection required.
    """
    from unity_cli.exceptions import ProjectError
    from unity_cli.hub.project import ProjectInfo

    context: CLIContext = ctx.obj
    try:
        info = ProjectInfo.from_path(path)

        if _should_json(context, json_flag):
            print_json(info.to_dict())
        else:
            from rich.panel import Panel
            from rich.table import Table

            # Basic info
            if is_no_color():
                print_line(f"{info.settings.product_name} ({info.path})")
            else:
                get_console().print(Panel(f"[bold]{info.settings.product_name}[/bold]", subtitle=str(info.path)))
            print_line(f"Company: {info.settings.company_name}")
            print_line(f"Version: {info.settings.version}")
            print_line(f"Unity: {info.unity_version.version}")
            if info.unity_version.revision:
                print_line(f"Revision: [dim]{info.unity_version.revision}[/dim]")
            print_line(f"Screen: {info.settings.default_screen_width}x{info.settings.default_screen_height}")
            print_line("")

            # Build scenes
            if info.build_settings.scenes:
                if is_no_color():
                    rows = [
                        [str(i), scene.path, "yes" if scene.enabled else "no"]
                        for i, scene in enumerate(info.build_settings.scenes)
                    ]
                    _print_plain_table(["#", "Path", "Enabled"], rows, "Build Scenes")
                else:
                    scene_table = Table(title="Build Scenes")
                    scene_table.add_column("#", style="dim")
                    scene_table.add_column("Path")
                    scene_table.add_column("Enabled")
                    for i, scene in enumerate(info.build_settings.scenes):
                        enabled = "[green]✓[/green]" if scene.enabled else "[red]✗[/red]"
                        scene_table.add_row(str(i), scene.path, enabled)
                    get_console().print(scene_table)
                print_line("")

            # Packages
            if info.packages.dependencies:
                if is_no_color():
                    rows = [
                        [pkg.name, pkg.version, "local" if pkg.is_local else ""] for pkg in info.packages.dependencies
                    ]
                    _print_plain_table(
                        ["Name", "Version", "Local"], rows, f"Packages ({len(info.packages.dependencies)})"
                    )
                else:
                    pkg_table = Table(title=f"Packages ({len(info.packages.dependencies)})")
                    pkg_table.add_column("Name", style="cyan")
                    pkg_table.add_column("Version")
                    pkg_table.add_column("Local")
                    for pkg in info.packages.dependencies:
                        local = "[yellow]local[/yellow]" if pkg.is_local else ""
                        pkg_table.add_row(pkg.name, pkg.version, local)
                    get_console().print(pkg_table)

    except ProjectError as e:
        _handle_error(e)


@project_app.command("version")
def project_version(
    ctx: typer.Context,
    path: Annotated[
        Path,
        typer.Argument(help="Unity project path"),
    ] = Path("."),
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Show Unity version for project."""
    from unity_cli.exceptions import ProjectVersionError
    from unity_cli.hub.project import ProjectVersion

    context: CLIContext = ctx.obj
    try:
        version = ProjectVersion.from_file(path)

        if _should_json(context, json_flag):
            print_json({"version": version.version, "revision": version.revision})
        else:
            print_line(f"Unity: [cyan]{version.version}[/cyan]")
            if version.revision:
                print_line(f"Revision: [dim]{version.revision}[/dim]")

    except ProjectVersionError as e:
        _handle_error(e)


@project_app.command("packages")
def project_packages(
    ctx: typer.Context,
    path: Annotated[
        Path,
        typer.Argument(help="Unity project path"),
    ] = Path("."),
    include_modules: Annotated[
        bool,
        typer.Option("--include-modules", help="Include Unity built-in modules"),
    ] = False,
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """List installed packages from manifest.json."""
    context: CLIContext = ctx.obj
    from unity_cli.hub.project import is_unity_project

    path = path.resolve()

    if not is_unity_project(path):
        print_error(f"Not a valid Unity project: {path}", "INVALID_PROJECT")
        raise typer.Exit(ExitCode.USAGE_ERROR) from None

    manifest_file = path / "Packages/manifest.json"
    if not manifest_file.exists():
        print_error("manifest.json not found", "MANIFEST_NOT_FOUND")
        raise typer.Exit(ExitCode.USAGE_ERROR) from None

    import json

    data = json.loads(manifest_file.read_text())
    deps = data.get("dependencies", {})

    packages = []
    for name, version in sorted(deps.items()):
        if not include_modules and name.startswith("com.unity.modules."):
            continue
        is_local = version.startswith("file:")
        packages.append({"name": name, "version": version, "local": is_local})

    if _should_json(context, json_flag):
        print_json(packages)
    else:
        if is_no_color():
            rows = [[pkg["name"], pkg["version"]] for pkg in packages]
            _print_plain_table(["Name", "Version"], rows, f"Packages ({len(packages)})")
        else:
            from rich.table import Table

            table = Table(title=f"Packages ({len(packages)})")
            table.add_column("Name", style="cyan")
            table.add_column("Version")
            for pkg in packages:
                version_str = f"[yellow]{pkg['version']}[/yellow]" if pkg["local"] else pkg["version"]
                table.add_row(pkg["name"], version_str)
            get_console().print(table)


@project_app.command("tags")
def project_tags(
    ctx: typer.Context,
    path: Annotated[
        Path,
        typer.Argument(help="Unity project path"),
    ] = Path("."),
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Show tags, layers, and sorting layers."""
    context: CLIContext = ctx.obj
    from unity_cli.hub.project import TagLayerSettings, is_unity_project

    path = path.resolve()

    if not is_unity_project(path):
        print_error(f"Not a valid Unity project: {path}", "INVALID_PROJECT")
        raise typer.Exit(ExitCode.USAGE_ERROR) from None

    settings = TagLayerSettings.from_file(path)

    if _should_json(context, json_flag):
        print_json(
            {
                "tags": settings.tags,
                "layers": [{"index": i, "name": n} for i, n in settings.layers],
                "sorting_layers": settings.sorting_layers,
            }
        )
    else:
        from rich.table import Table

        # Tags
        if settings.tags:
            print_line("[bold]Tags:[/bold]")
            for tag in settings.tags:
                print_line(f"  - {tag}")
            print_line("")
        else:
            print_line("[dim]No custom tags[/dim]")
            print_line("")

        # Layers
        if is_no_color():
            rows = [[str(idx), name] for idx, name in settings.layers]
            _print_plain_table(["#", "Name"], rows, "Layers")
        else:
            layer_table = Table(title="Layers")
            layer_table.add_column("#", style="dim", width=3)
            layer_table.add_column("Name", style="cyan")
            for idx, name in settings.layers:
                layer_table.add_row(str(idx), name)
            get_console().print(layer_table)
        print_line("")

        # Sorting Layers
        if settings.sorting_layers:
            print_line("[bold]Sorting Layers:[/bold]")
            for i, layer in enumerate(settings.sorting_layers):
                print_line(f"  {i}: {layer}")


@project_app.command("quality")
def project_quality(
    ctx: typer.Context,
    path: Annotated[
        Path,
        typer.Argument(help="Unity project path"),
    ] = Path("."),
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Show quality settings."""
    context: CLIContext = ctx.obj
    from unity_cli.hub.project import QualitySettings, is_unity_project

    path = path.resolve()

    if not is_unity_project(path):
        print_error(f"Not a valid Unity project: {path}", "INVALID_PROJECT")
        raise typer.Exit(ExitCode.USAGE_ERROR) from None

    settings = QualitySettings.from_file(path)

    if _should_json(context, json_flag):
        print_json(
            {
                "current_quality": settings.current_quality,
                "levels": [
                    {
                        "name": lvl.name,
                        "shadow_resolution": lvl.shadow_resolution,
                        "shadow_distance": lvl.shadow_distance,
                        "vsync_count": lvl.vsync_count,
                        "lod_bias": lvl.lod_bias,
                        "anti_aliasing": lvl.anti_aliasing,
                    }
                    for lvl in settings.levels
                ],
            }
        )
    else:
        title = f"Quality Levels (current: {settings.current_quality})"
        headers = ["#", "Name", "Shadow Res", "Shadow Dist", "VSync", "LOD Bias", "AA"]

        if is_no_color():
            rows = [
                [
                    f"{'>' if i == settings.current_quality else ' '}{i}",
                    lvl.name,
                    str(lvl.shadow_resolution),
                    str(lvl.shadow_distance),
                    str(lvl.vsync_count),
                    str(lvl.lod_bias),
                    str(lvl.anti_aliasing),
                ]
                for i, lvl in enumerate(settings.levels)
            ]
            _print_plain_table(headers, rows, title)
        else:
            from rich.table import Table

            table = Table(title=title)
            table.add_column("#", style="dim", width=3)
            table.add_column("Name", style="cyan")
            table.add_column("Shadow Res")
            table.add_column("Shadow Dist")
            table.add_column("VSync")
            table.add_column("LOD Bias")
            table.add_column("AA")
            for i, lvl in enumerate(settings.levels):
                marker = "[green]►[/green]" if i == settings.current_quality else " "
                table.add_row(
                    f"{marker}{i}",
                    lvl.name,
                    str(lvl.shadow_resolution),
                    str(lvl.shadow_distance),
                    str(lvl.vsync_count),
                    str(lvl.lod_bias),
                    str(lvl.anti_aliasing),
                )
            get_console().print(table)


@project_app.command("assemblies")
def project_assemblies(
    ctx: typer.Context,
    path: Annotated[
        Path,
        typer.Argument(help="Unity project path"),
    ] = Path("."),
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """List Assembly Definitions (.asmdef) in Assets/."""
    context: CLIContext = ctx.obj
    from unity_cli.hub.project import find_assembly_definitions, is_unity_project

    path = path.resolve()

    if not is_unity_project(path):
        print_error(f"Not a valid Unity project: {path}", "INVALID_PROJECT")
        raise typer.Exit(ExitCode.USAGE_ERROR) from None

    assemblies = find_assembly_definitions(path)

    if _should_json(context, json_flag):
        print_json(
            [
                {
                    "name": asm.name,
                    "path": str(asm.path.relative_to(path)),
                    "references": asm.references,
                    "include_platforms": asm.include_platforms,
                    "exclude_platforms": asm.exclude_platforms,
                    "allow_unsafe": asm.allow_unsafe,
                    "auto_referenced": asm.auto_referenced,
                }
                for asm in assemblies
            ]
        )
    else:
        if not assemblies:
            print_line("[dim]No Assembly Definitions found in Assets/[/dim]")
            return

        if is_no_color():
            rows = [
                [asm.name, str(asm.path.relative_to(path)), str(len(asm.references)), "yes" if asm.allow_unsafe else ""]
                for asm in assemblies
            ]
            _print_plain_table(["Name", "Path", "Refs", "Unsafe"], rows, f"Assembly Definitions ({len(assemblies)})")
        else:
            from rich.table import Table

            table = Table(title=f"Assembly Definitions ({len(assemblies)})")
            table.add_column("Name", style="cyan")
            table.add_column("Path", style="dim")
            table.add_column("Refs", justify="right")
            table.add_column("Unsafe")
            for asm in assemblies:
                rel_path = asm.path.relative_to(path)
                unsafe = "[yellow]✓[/yellow]" if asm.allow_unsafe else ""
                table.add_row(asm.name, str(rel_path), str(len(asm.references)), unsafe)
            get_console().print(table)


# =============================================================================
# Open Command
# =============================================================================


@app.command("open")
def open_project(
    path: Annotated[Path, typer.Argument(help="Unity project path")],
    editor_version: Annotated[
        str | None,
        typer.Option("--editor", "-e", help="Override editor version"),
    ] = None,
    non_interactive: Annotated[
        bool,
        typer.Option("--non-interactive", "-y", help="Fail instead of prompting"),
    ] = False,
    wait: Annotated[
        bool,
        typer.Option("--wait", "-w", help="Wait for editor to close"),
    ] = False,
) -> None:
    """Open Unity project with appropriate editor version.

    Reads ProjectSettings/ProjectVersion.txt to detect required version.
    If version not installed, prompts for action.
    """
    from unity_cli.exceptions import EditorNotFoundError, ProjectError
    from unity_cli.hub.service import HubService

    try:
        service = HubService()
        service.open_project(
            project_path=path,
            editor_override=editor_version,
            non_interactive=non_interactive,
            wait=wait,
        )
        print_success(f"Opened project: {path}")
    except (ProjectError, EditorNotFoundError) as e:
        _handle_error(e)


# =============================================================================
# Editor Commands (Unity Hub integration)
# =============================================================================

editor_app = typer.Typer(help="Unity Editor management (via Hub)")
app.add_typer(editor_app, name="editor")


@editor_app.command("list")
def editor_list(
    ctx: typer.Context,
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """List installed Unity editors."""
    context: CLIContext = ctx.obj
    from unity_cli.hub.paths import get_installed_editors

    editors = get_installed_editors()

    if _should_json(context, json_flag):
        data = [{"version": e.version, "path": str(e.path)} for e in editors]
        print_json(data)
    else:
        if not editors:
            print_line("[dim]No Unity editors found[/dim]")
            return

        if is_no_color():
            rows = [[editor.version, str(editor.path)] for editor in editors]
            _print_plain_table(["Version", "Path"], rows, f"Installed Editors ({len(editors)})")
        else:
            from rich.table import Table

            table = Table(title=f"Installed Editors ({len(editors)})")
            table.add_column("Version", style="cyan")
            table.add_column("Path", style="dim")
            for editor in editors:
                table.add_row(editor.version, str(editor.path))
            get_console().print(table)


@editor_app.command("install")
def editor_install(
    version: Annotated[str, typer.Argument(help="Unity version to install")],
    modules: Annotated[
        list[str] | None,
        typer.Option("--modules", "-m", help="Modules to install"),
    ] = None,
    changeset: Annotated[
        str | None,
        typer.Option("--changeset", "-c", help="Changeset for non-release versions"),
    ] = None,
) -> None:
    """Install Unity Editor via Hub CLI.

    Example: unity-cli editor install 2022.3.10f1 --modules android ios
    """
    from unity_cli.exceptions import HubError
    from unity_cli.hub.hub_cli import HubCLI

    try:
        hub = HubCLI()
        hub.install_editor(version=version, modules=modules, changeset=changeset)
        print_success(f"Installing Unity {version}")
        if modules:
            print_success(f"With modules: {', '.join(modules)}")
    except HubError as e:
        _handle_error(e)


# =============================================================================
# Selection Command
# =============================================================================


@app.command()
def selection(
    ctx: typer.Context,
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Get current editor selection."""
    context: CLIContext = ctx.obj
    try:
        result = context.client.selection.get()

        if _should_json(context, json_flag):
            print_json(result)
        else:
            count = result.get("count", 0)
            if count == 0:
                print_line("[dim]No objects selected[/dim]")
                return

            print_line(f"[bold]Selected: {count} object(s)[/bold]\n")

            active_go = result.get("activeGameObject")
            if active_go:
                print_line("[cyan]Active GameObject:[/cyan]")
                print_line(f"  Name: {escape(str(active_go.get('name', '')))}")
                print_line(f"  Instance ID: {active_go.get('instanceID')}")
                print_line(f"  Tag: {escape(str(active_go.get('tag', '')))}")
                print_line(f"  Layer: {escape(str(active_go.get('layerName', '')))} ({active_go.get('layer')})")
                print_line(f"  Path: {escape(str(active_go.get('scenePath', '')))}")

            active_transform = result.get("activeTransform")
            if active_transform:
                pos = active_transform.get("position", [])
                rot = active_transform.get("rotation", [])
                scale = active_transform.get("scale", [])
                print_line("\n[cyan]Transform:[/cyan]")
                if pos:
                    print_line(f"  Position: ({pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f})")
                if rot:
                    print_line(f"  Rotation: ({rot[0]:.2f}, {rot[1]:.2f}, {rot[2]:.2f})")
                if scale:
                    print_line(f"  Scale: ({scale[0]:.2f}, {scale[1]:.2f}, {scale[2]:.2f})")

            game_objects = result.get("gameObjects", [])
            if len(game_objects) > 1:
                print_line(f"\n[cyan]All Selected GameObjects ({len(game_objects)}):[/cyan]")
                for go in game_objects:
                    print_line(f"  - {escape(str(go.get('name', '')))} (ID: {go.get('instanceID')})")

    except UnityCLIError as e:
        _handle_error(e)


# =============================================================================
# Screenshot Command
# =============================================================================


@app.command()
def screenshot(
    ctx: typer.Context,
    source: Annotated[
        str,
        typer.Option("--source", "-s", help="Capture source: game, scene, or camera"),
    ] = "game",
    path: Annotated[
        str | None,
        typer.Option("--path", "-p", help="Output file path"),
    ] = None,
    super_size: Annotated[
        int,
        typer.Option("--super-size", help="Resolution multiplier (1-4, game only)"),
    ] = 1,
    width: Annotated[
        int | None,
        typer.Option("--width", "-W", help="Image width (camera only, default: 1920)"),
    ] = None,
    height: Annotated[
        int | None,
        typer.Option("--height", "-H", help="Image height (camera only, default: 1080)"),
    ] = None,
    camera_name: Annotated[
        str | None,
        typer.Option("--camera", "-c", help="Camera name (camera only, default: Main Camera)"),
    ] = None,
) -> None:
    """Capture screenshot from GameView, SceneView, or Camera.

    Sources:
      game   - GameView (async, requires editor focus)
      scene  - SceneView
      camera - Camera.Render (sync, focus-independent)
    """
    context: CLIContext = ctx.obj

    if source not in ("game", "scene", "camera"):
        print_error(f"Invalid source: {source}. Use 'game', 'scene', or 'camera'", "INVALID_SOURCE")
        raise typer.Exit(ExitCode.USAGE_ERROR) from None

    try:
        result = context.client.screenshot.capture(
            source=source,  # type: ignore[arg-type]
            path=path,
            super_size=super_size,
            width=width,
            height=height,
            camera=camera_name,
        )

        print_success(f"Screenshot captured: {result.get('path')}")
        if result.get("note"):
            print_line(f"[dim]{result.get('note')}[/dim]")
        if result.get("camera"):
            print_line(f"[dim]Camera: {result.get('camera')}[/dim]")

    except UnityCLIError as e:
        _handle_error(e)


# =============================================================================
# Completion Commands
# =============================================================================

_COMPLETION_SCRIPTS = {
    "zsh": """#compdef u unity unity-cli

_unity_cli() {
  eval $(env _TYPER_COMPLETE_ARGS="${words[1,$CURRENT]}" _U_COMPLETE=complete_zsh u)
}

_unity_cli "$@"
""",
    "bash": """_unity_cli() {
  local IFS=$'\\n'
  COMPREPLY=($(env _TYPER_COMPLETE_ARGS="${COMP_WORDS[*]}" _U_COMPLETE=complete_bash u))
  return 0
}

complete -o default -F _unity_cli u unity unity-cli
""",
    "fish": """complete -c u -f -a "(env _TYPER_COMPLETE_ARGS=(commandline -cp) _U_COMPLETE=complete_fish u)"
complete -c unity -f -a "(env _TYPER_COMPLETE_ARGS=(commandline -cp) _U_COMPLETE=complete_fish unity)"
complete -c unity-cli -f -a "(env _TYPER_COMPLETE_ARGS=(commandline -cp) _U_COMPLETE=complete_fish unity-cli)"
""",
}


@app.command("completion")
def completion(
    shell: Annotated[
        str | None,
        typer.Option("--shell", "-s", help="Shell type: zsh, bash, fish"),
    ] = None,
) -> None:
    """Generate shell completion script.

    Examples:
        u completion -s zsh > ~/.zsh/completions/_unity-cli
        u completion -s bash >> ~/.bashrc
        u completion -s fish > ~/.config/fish/completions/unity-cli.fish
    """
    import os

    # Auto-detect shell if not specified
    if shell is None:
        shell_env = os.environ.get("SHELL", "")
        if "zsh" in shell_env:
            shell = "zsh"
        elif "bash" in shell_env:
            shell = "bash"
        elif "fish" in shell_env:
            shell = "fish"
        else:
            shell = "zsh"  # Default to zsh

    shell = shell.lower()
    if shell not in _COMPLETION_SCRIPTS:
        import sys

        if is_no_color():
            print(f"Unsupported shell: {shell}", file=sys.stderr)
            print(f"Supported shells: {', '.join(_COMPLETION_SCRIPTS.keys())}", file=sys.stderr)
        else:
            get_err_console().print(f"[red]Unsupported shell: {shell}[/red]")
            get_err_console().print(f"Supported shells: {', '.join(_COMPLETION_SCRIPTS.keys())}")
        raise typer.Exit(ExitCode.USAGE_ERROR)

    # Output script to stdout (no Rich formatting)
    print(_COMPLETION_SCRIPTS[shell], end="")


# =============================================================================
# Entry Point
# =============================================================================


def cli_main() -> None:
    """CLI entry point."""
    app()


if __name__ == "__main__":
    cli_main()
