"""Scene management commands: active, hierarchy, load, save."""

from __future__ import annotations

from typing import Annotated

import typer

from unity_cli.cli.context import CLIContext
from unity_cli.cli.helpers import _exit_usage, _handle_error, _should_json
from unity_cli.cli.output import print_hierarchy_table, print_json, print_key_value, print_success
from unity_cli.exceptions import UnityCLIError

scene_app = typer.Typer(help="Scene management commands")


@scene_app.command("active")
def scene_active(
    ctx: typer.Context,
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Get active scene info."""
    context: CLIContext = ctx.obj
    try:
        result = context.client.scene.get_active()
        if _should_json(context, json_flag):
            print_json(result, None)
        else:
            print_key_value(result, "Active Scene")
    except UnityCLIError as e:
        _handle_error(e)


@scene_app.command("hierarchy")
def scene_hierarchy(
    ctx: typer.Context,
    depth: Annotated[int, typer.Option("--depth", "-d", help="Hierarchy depth")] = 1,
    page_size: Annotated[int, typer.Option("--page-size", help="Page size")] = 50,
    cursor: Annotated[int, typer.Option("--cursor", help="Pagination cursor")] = 0,
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Get scene hierarchy."""
    context: CLIContext = ctx.obj
    try:
        result = context.client.scene.get_hierarchy(
            depth=depth,
            page_size=page_size,
            cursor=cursor,
        )
        if _should_json(context, json_flag):
            print_json(result)
        else:
            print_hierarchy_table(result.get("items", []))
    except UnityCLIError as e:
        _handle_error(e)


@scene_app.command("load")
def scene_load(
    ctx: typer.Context,
    path: Annotated[str | None, typer.Option("--path", "-p", help="Scene path")] = None,
    name: Annotated[str | None, typer.Option("--name", "-n", help="Scene name")] = None,
    additive: Annotated[bool, typer.Option("--additive", "-a", help="Load additively")] = False,
) -> None:
    """Load a scene."""
    context: CLIContext = ctx.obj

    if not path and not name:
        _exit_usage("--path or --name required", "u scene load")

    try:
        result = context.client.scene.load(path=path, name=name, additive=additive)
        print_success(result.get("message", "Scene loaded"))
    except UnityCLIError as e:
        _handle_error(e)


@scene_app.command("save")
def scene_save(
    ctx: typer.Context,
    path: Annotated[str | None, typer.Option("--path", "-p", help="Save path")] = None,
) -> None:
    """Save current scene."""
    context: CLIContext = ctx.obj
    try:
        result = context.client.scene.save(path=path)
        print_success(result.get("message", "Scene saved"))
    except UnityCLIError as e:
        _handle_error(e)
