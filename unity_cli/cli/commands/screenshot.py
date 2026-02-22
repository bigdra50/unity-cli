"""Screenshot command: capture (default) and burst mode."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.markup import escape

from unity_cli.cli.context import CLIContext
from unity_cli.cli.exit_codes import ExitCode
from unity_cli.cli.helpers import _handle_error, _should_json
from unity_cli.cli.output import OutputMode, get_output_mode, print_error, print_json, print_line, print_success
from unity_cli.exceptions import UnityCLIError


def screenshot(
    ctx: typer.Context,
    burst: Annotated[
        bool,
        typer.Option("--burst", help="Burst mode: capture multiple frames in rapid succession"),
    ] = False,
    # --- capture options ---
    source: Annotated[
        str,
        typer.Option("--source", "-s", help="Capture source: game, scene, or camera"),
    ] = "game",
    path: Annotated[
        str | None,
        typer.Option("--path", "-p", help="Output file path (capture only)"),
    ] = None,
    super_size: Annotated[
        int,
        typer.Option("--super-size", help="Resolution multiplier (1-4, game only)"),
    ] = 1,
    # --- burst options ---
    count: Annotated[
        int,
        typer.Option("--count", "-n", help="Number of frames to capture (burst only)"),
    ] = 10,
    interval_ms: Annotated[
        int,
        typer.Option("--interval", help="Minimum interval between frames in ms (burst only, 0 = fastest)"),
    ] = 0,
    output_dir: Annotated[
        str | None,
        typer.Option("--output", "-o", help="Output directory (burst only)"),
    ] = None,
    # --- common options ---
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Image format: png or jpg"),
    ] = "png",
    quality: Annotated[
        int,
        typer.Option("--quality", "-q", help="JPEG quality 1-100 (jpg only)"),
    ] = 75,
    width: Annotated[
        int | None,
        typer.Option("--width", "-W", help="Image width (camera/burst only)"),
    ] = None,
    height: Annotated[
        int | None,
        typer.Option("--height", "-H", help="Image height (camera/burst only)"),
    ] = None,
    camera_name: Annotated[
        str | None,
        typer.Option("--camera", "-c", help="Camera name"),
    ] = None,
    json_flag: Annotated[
        bool,
        typer.Option("--json", "-j", help="Output as JSON"),
    ] = False,
) -> None:
    """Capture screenshot from GameView, SceneView, or Camera.

    By default captures a single screenshot. Use --burst for multi-frame capture.

    Sources (capture mode):
      game   - GameView (async, requires editor focus)
      scene  - SceneView
      camera - Camera.Render (sync, focus-independent)
    """
    if burst:
        _burst(ctx, count, interval_ms, format, quality, width, height, camera_name, output_dir, json_flag)
    else:
        _capture(ctx, source, path, super_size, format, quality, width, height, camera_name, json_flag)


def _capture(
    ctx: typer.Context,
    source: str,
    path: str | None,
    super_size: int,
    format: str,
    quality: int,
    width: int | None,
    height: int | None,
    camera_name: str | None,
    json_flag: bool,
) -> None:
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


def _burst(
    ctx: typer.Context,
    count: int,
    interval_ms: int,
    format: str,
    quality: int,
    width: int | None,
    height: int | None,
    camera_name: str | None,
    output_dir: str | None,
    json_flag: bool,
) -> None:
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
