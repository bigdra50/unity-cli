"""Basic editor control commands: version, instances, state, play, stop, pause, refresh."""

from __future__ import annotations

from importlib.metadata import version as pkg_version
from typing import Annotated

import typer

from unity_cli.cli.context import CLIContext
from unity_cli.cli.helpers import _handle_error, _should_json
from unity_cli.cli.output import (
    print_instances_table,
    print_json,
    print_key_value,
    print_line,
    print_success,
)
from unity_cli.exceptions import UnityCLIError


def register(app: typer.Typer) -> None:
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
        """List Unity Editor instances currently registered with the Relay Server.

        Each row shows the project path/name and its instance ID. Use the name
        or path prefix with --instance/-i on any command to target a specific
        editor when more than one is open.
        """
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
        """Return current editor state: play mode, pause, compilation, active scene.

        Useful as a readiness probe before scripting other commands.
        """
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
        """Enter Play Mode (equivalent to pressing the Play button in the editor)."""
        context: CLIContext = ctx.obj
        try:
            context.client.editor.play()
            print_success("Entered play mode")
        except UnityCLIError as e:
            _handle_error(e)

    @app.command()
    def stop(ctx: typer.Context) -> None:
        """Exit Play Mode and return to Edit Mode."""
        context: CLIContext = ctx.obj
        try:
            context.client.editor.stop()
            print_success("Exited play mode")
        except UnityCLIError as e:
            _handle_error(e)

    @app.command()
    def pause(ctx: typer.Context) -> None:
        """Toggle Play Mode pause (has no effect when not in Play Mode)."""
        context: CLIContext = ctx.obj
        try:
            context.client.editor.pause()
            print_success("Toggled pause")
        except UnityCLIError as e:
            _handle_error(e)

    @app.command()
    def refresh(ctx: typer.Context) -> None:
        """Run AssetDatabase.Refresh — reimport changed assets and recompile scripts.

        Equivalent to 'Assets > Refresh' / Ctrl+R in the editor. Use after editing
        C# files from outside Unity to force a compile.
        """
        context: CLIContext = ctx.obj
        try:
            context.client.editor.refresh()
            print_success("Asset database refreshed")
        except UnityCLIError as e:
            _handle_error(e)
