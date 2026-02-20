"""Screenshot command."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.markup import escape

from unity_cli.cli.context import CLIContext
from unity_cli.cli.exit_codes import ExitCode
from unity_cli.cli.helpers import _handle_error, _should_json
from unity_cli.cli.output import OutputMode, get_output_mode, print_error, print_json, print_line, print_success
from unity_cli.exceptions import UnityCLIError


def register(app: typer.Typer) -> None:
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

        try:
            result = context.client.screenshot.capture(
                source=source,  # type: ignore[arg-type]
                path=path,
                super_size=super_size,
                width=width,
                height=height,
                camera=camera_name,
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

        except UnityCLIError as e:
            _handle_error(e)
