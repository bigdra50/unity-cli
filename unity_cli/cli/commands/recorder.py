"""Recorder commands: start, stop, status."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.markup import escape

from unity_cli.cli.context import CLIContext
from unity_cli.cli.exit_codes import ExitCode
from unity_cli.cli.helpers import _handle_error, _should_json
from unity_cli.cli.output import (
    print_error,
    print_json,
    print_line,
    print_success,
)
from unity_cli.exceptions import UnityCLIError

recorder_app = typer.Typer(help="Frame recording commands")


@recorder_app.command("start")
def recorder_start(
    ctx: typer.Context,
    fps: Annotated[
        int,
        typer.Option("--fps", help="Target frames per second"),
    ] = 30,
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Image format: png or jpg"),
    ] = "jpg",
    quality: Annotated[
        int,
        typer.Option("--quality", "-q", help="JPEG quality 1-100 (jpg only)"),
    ] = 75,
    width: Annotated[
        int | None,
        typer.Option("--width", "-W", help="Image width (default: 1920)"),
    ] = None,
    height: Annotated[
        int | None,
        typer.Option("--height", "-H", help="Image height (default: 1080)"),
    ] = None,
    camera_name: Annotated[
        str | None,
        typer.Option("--camera", "-c", help="Camera name (default: Main Camera)"),
    ] = None,
    output_dir: Annotated[
        str | None,
        typer.Option("--output", "-o", help="Output directory"),
    ] = None,
    json_flag: Annotated[
        bool,
        typer.Option("--json", "-j", help="Output as JSON"),
    ] = False,
) -> None:
    """Start recording frames from camera."""
    context: CLIContext = ctx.obj

    if format not in ("png", "jpg"):
        print_error(f"Invalid format: {format}. Use 'png' or 'jpg'", "INVALID_FORMAT")
        raise typer.Exit(ExitCode.USAGE_ERROR) from None

    try:
        result = context.client.recorder.start(
            fps=fps,
            format=format,  # type: ignore[arg-type]
            quality=quality,
            width=width or 1920,
            height=height or 1080,
            camera=camera_name,
            output_dir=output_dir,
        )

        if _should_json(context, json_flag):
            print_json(result)
            return

        print_success(result.get("message", "Recording started"))
        out_dir = result.get("outputDir", "")
        if out_dir:
            print_line(f"[dim]Output: {escape(str(out_dir))}[/dim]")

    except UnityCLIError as e:
        _handle_error(e)


@recorder_app.command("stop")
def recorder_stop(
    ctx: typer.Context,
    json_flag: Annotated[
        bool,
        typer.Option("--json", "-j", help="Output as JSON"),
    ] = False,
) -> None:
    """Stop recording and get results."""
    context: CLIContext = ctx.obj

    try:
        result = context.client.recorder.stop()

        if _should_json(context, json_flag):
            print_json(result)
            return

        frame_count = result.get("frameCount", 0)
        elapsed = result.get("elapsed", 0)
        fps = result.get("fps", 0)
        out_dir = result.get("outputDir", "")
        print_success(f"Recording stopped: {frame_count} frames in {elapsed}s ({fps} FPS)")
        print_line(f"[dim]Output: {escape(str(out_dir))}[/dim]")

    except UnityCLIError as e:
        _handle_error(e)


@recorder_app.command("status")
def recorder_status(
    ctx: typer.Context,
    json_flag: Annotated[
        bool,
        typer.Option("--json", "-j", help="Output as JSON"),
    ] = False,
) -> None:
    """Check recording status."""
    context: CLIContext = ctx.obj

    try:
        result = context.client.recorder.status()

        if _should_json(context, json_flag):
            print_json(result)
            return

        recording = result.get("recording", False)
        if not recording:
            print_line("[dim]No recording in progress[/dim]")
            return

        frame_count = result.get("frameCount", 0)
        elapsed = result.get("elapsed", 0)
        fps = result.get("fps", 0)
        pending = result.get("pendingWrites", 0)
        print_line(f"[green]Recording[/green] {frame_count} frames ({elapsed}s, {fps} FPS)")
        if pending > 0:
            print_line(f"[dim]Pending writes: {pending}[/dim]")

    except UnityCLIError as e:
        _handle_error(e)
