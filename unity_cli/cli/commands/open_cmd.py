"""Open project command."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from unity_cli.cli.helpers import _handle_error
from unity_cli.cli.output import print_success


def register(app: typer.Typer) -> None:
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
