"""Profiler commands: status, start, stop, snapshot, frames."""

from __future__ import annotations

from typing import Annotated

import typer

from unity_cli.cli.context import CLIContext
from unity_cli.cli.helpers import _handle_error, _should_json
from unity_cli.cli.output import (
    _print_plain_table,
    get_console,
    is_no_color,
    print_json,
    print_line,
    print_success,
    print_warning,
)
from unity_cli.exceptions import UnityCLIError

profiler_app = typer.Typer(help="Profiler commands")


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
