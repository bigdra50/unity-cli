"""Selection command."""

from __future__ import annotations

from typing import Annotated, Any

import typer
from rich.markup import escape

from unity_cli.cli.context import CLIContext
from unity_cli.cli.helpers import _handle_error, _should_json
from unity_cli.cli.output import is_no_color, print_json, print_key_value, print_line, print_plain_table
from unity_cli.exceptions import UnityCLIError


def register(app: typer.Typer) -> None:
    @app.command()
    def selection(
        ctx: typer.Context,
        json_flag: Annotated[
            bool,
            typer.Option("--json", help="Output as JSON"),
        ] = False,
    ) -> None:
        """Return the GameObject(s) currently selected in the Hierarchy/Scene view.

        Reports count, the active selection's name/instance ID/tag/layer/scene path,
        its Transform (position/rotation/scale), and the full list when multiple
        objects are selected. Empty output means nothing is selected.
        """
        context: CLIContext = ctx.obj
        try:
            result = context.client.selection.get()

            if _should_json(context, json_flag):
                print_json(result)
            else:
                _print_selection(result)

        except UnityCLIError as e:
            _handle_error(e)


def _print_selection_plain(result: dict[str, Any]) -> None:
    count = result.get("count", 0)
    if count == 0:
        return
    game_objects = result.get("gameObjects", [])
    if count == 1 or not game_objects:
        active_go = result.get("activeGameObject")
        if active_go:
            print_key_value(
                {
                    "name": active_go.get("name", ""),
                    "instanceID": active_go.get("instanceID", ""),
                    "tag": active_go.get("tag", ""),
                    "layer": active_go.get("layerName", ""),
                    "path": active_go.get("scenePath", ""),
                }
            )
    else:
        rows = [
            [
                go.get("name", ""),
                str(go.get("instanceID", "")),
                go.get("tag", ""),
                go.get("layerName", ""),
                go.get("scenePath", ""),
            ]
            for go in game_objects
        ]
        print_plain_table(["Name", "ID", "Tag", "Layer", "Path"], rows, header=False)


def _print_selection(result: dict[str, Any]) -> None:
    count = result.get("count", 0)

    if is_no_color():
        _print_selection_plain(result)
        return

    if count == 0:
        print_line("[dim]No objects selected[/dim]")
        return

    print_line(f"[bold]Selected: {count} object(s)[/bold]\n")

    active_go = result.get("activeGameObject")
    if active_go:
        print_line("[cyan]Active GameObject:[/cyan]")
        for label, key in [("Name", "name"), ("Instance ID", "instanceID"), ("Tag", "tag")]:
            print_line(f"  {label}: {escape(str(active_go.get(key, '')))}")
        print_line(f"  Layer: {escape(str(active_go.get('layerName', '')))} ({active_go.get('layer')})")
        print_line(f"  Path: {escape(str(active_go.get('scenePath', '')))}")

    _print_transform(result.get("activeTransform"))

    game_objects = result.get("gameObjects", [])
    if len(game_objects) > 1:
        print_line(f"\n[cyan]All Selected GameObjects ({len(game_objects)}):[/cyan]")
        for go in game_objects:
            print_line(f"  - {escape(str(go.get('name', '')))} (ID: {go.get('instanceID')})")


def _print_transform(transform: dict[str, Any] | None) -> None:
    if not transform:
        return
    print_line("\n[cyan]Transform:[/cyan]")
    for label, key in [("Position", "position"), ("Rotation", "rotation"), ("Scale", "scale")]:
        vec = transform.get(key, [])
        if vec:
            print_line(f"  {label}: ({vec[0]:.2f}, {vec[1]:.2f}, {vec[2]:.2f})")
