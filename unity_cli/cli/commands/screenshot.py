"""Screenshot commands: capture and burst."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.markup import escape

from unity_cli.cli.context import CLIContext
from unity_cli.cli.exit_codes import ExitCode
from unity_cli.cli.helpers import _handle_error, _should_json
from unity_cli.cli.output import OutputMode, get_output_mode, print_error, print_json, print_line, print_success
from unity_cli.exceptions import UnityCLIError

screenshot_app = typer.Typer(help="Screenshot capture commands")


@screenshot_app.command("capture")
def screenshot_capture(
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
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Image format: png or jpg"),
    ] = "png",
    quality: Annotated[
        int,
        typer.Option("--quality", "-q", help="JPEG quality 1-100 (jpg only)"),
    ] = 75,
    json_flag: Annotated[
        bool,
        typer.Option("--json", "-j", help="Output as JSON"),
    ] = False,
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

    if format not in ("png", "jpg"):
        print_error(f"Invalid format: {format}. Use 'png' or 'jpg'", "INVALID_FORMAT")
        raise typer.Exit(ExitCode.USAGE_ERROR) from None

    try:
        result = context.client.screenshot.capture(
            source=source,  # type: ignore[arg-type]
            path=path,
            super_size=super_size,
            width=width,
            height=height,
            camera=camera_name,
            format=format,  # type: ignore[arg-type]
            quality=quality,
        )

        captured_path = result.get("path", "")

        if _should_json(context, json_flag):
            print_json(result)
            return

        if get_output_mode() is not OutputMode.PRETTY:
            print(captured_path)
            return

        print_success(f"Screenshot captured: {captured_path}")
        if result.get("note"):
            print_line(f"[dim]{escape(str(result.get('note')))}[/dim]")
        if result.get("camera"):
            print_line(f"[dim]Camera: {escape(str(result.get('camera')))}[/dim]")
        if result.get("format"):
            print_line(f"[dim]Format: {escape(str(result.get('format')))}[/dim]")

    except UnityCLIError as e:
        _handle_error(e)


@screenshot_app.command("burst")
def screenshot_burst(
    ctx: typer.Context,
    count: Annotated[
        int,
        typer.Option("--count", "-n", help="Number of frames to capture"),
    ] = 10,
    interval_ms: Annotated[
        int,
        typer.Option("--interval", help="Minimum interval between frames in ms (0 = fastest)"),
    ] = 0,
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
    """Capture multiple frames in rapid succession (burst mode)."""
    context: CLIContext = ctx.obj

    if format not in ("png", "jpg"):
        print_error(f"Invalid format: {format}. Use 'png' or 'jpg'", "INVALID_FORMAT")
        raise typer.Exit(ExitCode.USAGE_ERROR) from None

    try:
        result = context.client.screenshot.burst(
            count=count,
            interval_ms=interval_ms,
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

        if get_output_mode() is not OutputMode.PRETTY:
            print(result.get("outputDir", ""))
            return

        frame_count = result.get("frameCount", 0)
        elapsed = result.get("elapsed", 0)
        fps = result.get("fps", 0)
        out_dir = result.get("outputDir", "")
        print_success(f"Burst capture: {frame_count} frames in {elapsed}s ({fps} FPS)")
        print_line(f"[dim]Output: {escape(str(out_dir))}[/dim]")

    except UnityCLIError as e:
        _handle_error(e)
