"""GameObject commands: find, create, modify, active, delete."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.markup import escape

from unity_cli.cli.context import CLIContext
from unity_cli.cli.helpers import _exit_usage, _should_json, handle_cli_errors
from unity_cli.cli.output import print_json, print_line, print_success

gameobject_app = typer.Typer(help="GameObject commands")


@gameobject_app.command("find")
@handle_cli_errors
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


@gameobject_app.command("create")
@handle_cli_errors
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
    result = context.client.gameobject.create(
        name=name,
        primitive_type=primitive,
        position=list(position) if position else None,
        rotation=list(rotation) if rotation else None,
        scale=list(scale) if scale else None,
    )
    print_success(result.get("message", f"Created: {name}"))


@gameobject_app.command("modify")
@handle_cli_errors
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

    result = context.client.gameobject.modify(
        name=name,
        instance_id=id,
        position=list(position) if position else None,
        rotation=list(rotation) if rotation else None,
        scale=list(scale) if scale else None,
    )
    print_success(result.get("message", "Transform modified"))


@gameobject_app.command("active")
@handle_cli_errors
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

    result = context.client.gameobject.set_active(
        active=active,
        name=name,
        instance_id=id,
    )
    print_success(result.get("message", f"Active set to {active}"))


@gameobject_app.command("delete")
@handle_cli_errors
def gameobject_delete(
    ctx: typer.Context,
    name: Annotated[str | None, typer.Option("--name", "-n", help="GameObject name")] = None,
    id: Annotated[int | None, typer.Option("--id", help="Instance ID")] = None,
) -> None:
    """Delete a GameObject."""
    context: CLIContext = ctx.obj

    if not name and id is None:
        _exit_usage("--name or --id required", "u gameobject delete")

    result = context.client.gameobject.delete(name=name, instance_id=id)
    print_success(result.get("message", "GameObject deleted"))
