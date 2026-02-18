"""Build pipeline commands: settings, run, scenes."""

from __future__ import annotations

from typing import Annotated, Any

import typer
from rich.markup import escape

from unity_cli.cli.context import CLIContext
from unity_cli.cli.exit_codes import ExitCode
from unity_cli.cli.helpers import _handle_error, _should_json
from unity_cli.cli.output import (
    _print_plain_table,
    get_console,
    is_no_color,
    print_error,
    print_json,
    print_line,
    print_success,
)
from unity_cli.exceptions import UnityCLIError

build_app = typer.Typer(help="Build pipeline commands")


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
                ("Target", str(result.get("target", ""))),
                ("Target Group", str(result.get("targetGroup", ""))),
                ("Product Name", str(result.get("productName", ""))),
                ("Company Name", str(result.get("companyName", ""))),
                ("Bundle Version", str(result.get("bundleVersion", ""))),
                ("Scripting Backend", str(result.get("scriptingBackend", ""))),
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
                raise typer.Exit(ExitCode.OPERATION_ERROR) from None
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
            scenes_list: list[dict[str, Any]] = result.get("scenes", [])

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
