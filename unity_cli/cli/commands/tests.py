"""Test execution commands: run, list, status."""

from __future__ import annotations

from typing import Annotated, Any

import typer
from rich.markup import escape

from unity_cli.cli.context import CLIContext
from unity_cli.cli.exit_codes import ExitCode
from unity_cli.cli.helpers import _handle_error, _should_json
from unity_cli.cli.output import (
    get_err_console,
    is_no_color,
    print_info,
    print_json,
    print_key_value,
    print_line,
    print_success,
    print_warning,
)
from unity_cli.exceptions import UnityCLIError

tests_app = typer.Typer(help="Test execution commands")


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
            raise typer.Exit(ExitCode.TEST_FAILURE)
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
