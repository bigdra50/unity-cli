"""GameObject commands: find, create, modify, active, delete."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.markup import escape

from unity_cli.cli.context import CLIContext
from unity_cli.cli.helpers import _exit_usage, _handle_error, _should_json
from unity_cli.cli.output import print_json, print_line, print_success
from unity_cli.exceptions import UnityCLIError

gameobject_app = typer.Typer(help="GameObject commands")


@gameobject_app.command("find")
def gameobject_find(
    ctx: typer.Context,
    name: Annotated[str | None, typer.Option("--name", "-n", help="GameObject name")] = None,
    id: Annotated[int | None, typer.Option("--id", help="Instance ID")] = None,
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Find GameObjects by name or ID."""
    context: CLIContext = ctx.obj

    if not name and id is None:
        _exit_usage("--name or --id required", "u gameobject find")

    try:
        result = context.client.gameobject.find(name=name, instance_id=id)
        if _should_json(context, json_flag):
            print_json(result)
        else:
            objects = result.get("objects", [])
            print_line(f"[bold]Found {len(objects)} GameObject(s)[/bold]")
            for obj in objects:
                obj_name = escape(obj.get("name", "Unknown"))
                obj_id = obj.get("instanceID", "")
                print_line(f"  {obj_name} (ID: {obj_id})")
    except UnityCLIError as e:
        _handle_error(e)


@gameobject_app.command("create")
def gameobject_create(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name", "-n", help="GameObject name")],
    primitive: Annotated[
        str | None,
        typer.Option("--primitive", "-p", help="Primitive type (Cube, Sphere, etc.)"),
    ] = None,
    position: Annotated[
        tuple[float, float, float] | None,
        typer.Option("--position", help="Position (X Y Z)"),
    ] = None,
    rotation: Annotated[
        tuple[float, float, float] | None,
        typer.Option("--rotation", help="Rotation (X Y Z)"),
    ] = None,
    scale: Annotated[
        tuple[float, float, float] | None,
        typer.Option("--scale", help="Scale (X Y Z)"),
    ] = None,
) -> None:
    """Create a new GameObject."""
    context: CLIContext = ctx.obj
    try:
        result = context.client.gameobject.create(
            name=name,
            primitive_type=primitive,
            position=list(position) if position else None,
            rotation=list(rotation) if rotation else None,
            scale=list(scale) if scale else None,
        )
        print_success(result.get("message", f"Created: {name}"))
    except UnityCLIError as e:
        _handle_error(e)


@gameobject_app.command("modify")
def gameobject_modify(
    ctx: typer.Context,
    name: Annotated[str | None, typer.Option("--name", "-n", help="GameObject name")] = None,
    id: Annotated[int | None, typer.Option("--id", help="Instance ID")] = None,
    position: Annotated[
        tuple[float, float, float] | None,
        typer.Option("--position", help="Position (X Y Z)"),
    ] = None,
    rotation: Annotated[
        tuple[float, float, float] | None,
        typer.Option("--rotation", help="Rotation (X Y Z)"),
    ] = None,
    scale: Annotated[
        tuple[float, float, float] | None,
        typer.Option("--scale", help="Scale (X Y Z)"),
    ] = None,
) -> None:
    """Modify GameObject transform."""
    context: CLIContext = ctx.obj

    if not name and id is None:
        _exit_usage("--name or --id required", "u gameobject modify")

    try:
        result = context.client.gameobject.modify(
            name=name,
            instance_id=id,
            position=list(position) if position else None,
            rotation=list(rotation) if rotation else None,
            scale=list(scale) if scale else None,
        )
        print_success(result.get("message", "Transform modified"))
    except UnityCLIError as e:
        _handle_error(e)


@gameobject_app.command("active")
def gameobject_active(
    ctx: typer.Context,
    name: Annotated[str | None, typer.Option("--name", "-n", help="GameObject name")] = None,
    id: Annotated[int | None, typer.Option("--id", help="Instance ID")] = None,
    active: Annotated[
        bool,
        typer.Option("--active/--no-active", help="Set active (true) or inactive (false)"),
    ] = True,
) -> None:
    """Set GameObject active state."""
    context: CLIContext = ctx.obj

    if not name and id is None:
        _exit_usage("--name or --id required", "u gameobject active")

    try:
        result = context.client.gameobject.set_active(
            active=active,
            name=name,
            instance_id=id,
        )
        print_success(result.get("message", f"Active set to {active}"))
    except UnityCLIError as e:
        _handle_error(e)


@gameobject_app.command("delete")
def gameobject_delete(
    ctx: typer.Context,
    name: Annotated[str | None, typer.Option("--name", "-n", help="GameObject name")] = None,
    id: Annotated[int | None, typer.Option("--id", help="Instance ID")] = None,
) -> None:
    """Delete a GameObject."""
    context: CLIContext = ctx.obj

    if not name and id is None:
        _exit_usage("--name or --id required", "u gameobject delete")

    try:
        result = context.client.gameobject.delete(name=name, instance_id=id)
        print_success(result.get("message", "GameObject deleted"))
    except UnityCLIError as e:
        _handle_error(e)
