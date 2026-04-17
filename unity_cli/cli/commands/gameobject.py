"""GameObject commands: find, create, modify, active, delete."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.markup import escape

from unity_cli.cli.context import CLIContext
from unity_cli.cli.helpers import _exit_usage, _should_json, handle_cli_errors
from unity_cli.cli.output import is_no_color, print_json, print_line, print_plain_table, print_success

gameobject_app = typer.Typer(
    help=(
        "Create, find, modify, (de)activate, and delete GameObjects in the active scene.\n\n"
        "Targets can be specified by name (first match) or instance ID. Transforms are\n"
        "edited via --position / --rotation / --scale. Combine with the 'component'\n"
        "commands to attach or tweak components on the resulting objects."
    )
)


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
    """Locate GameObjects in the active scene by name or instance ID.

    Returns all matching objects with their instance IDs — use the ID for
    precise follow-up commands when multiple share a name.

    Examples:
        u gameobject find -n Player
        u gameobject find --id 12345
    """
    context: CLIContext = ctx.obj

    if not name and id is None:
        _exit_usage("--name or --id required", "u gameobject find")

    result = context.client.gameobject.find(name=name, instance_id=id)
    if _should_json(context, json_flag):
        print_json(result)
    else:
        objects = result.get("objects", [])
        if is_no_color():
            rows = [[obj.get("name", "Unknown"), str(obj.get("instanceID", ""))] for obj in objects]
            print_plain_table(["Name", "ID"], rows, header=False)
        else:
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
        typer.Option(
            "--primitive",
            "-p",
            help="Primitive type: Cube, Sphere, Capsule, Cylinder, Plane, Quad (omit for empty GameObject)",
        ),
    ] = None,
    parent: Annotated[
        str | None,
        typer.Option("--parent", help="Parent GameObject name"),
    ] = None,
    parent_id: Annotated[
        int | None,
        typer.Option("--parent-id", help="Parent GameObject instance ID"),
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
    """Create a GameObject (empty or primitive) in the active scene.

    Omit --primitive for an empty GameObject. Pass one of the primitive types
    (Cube/Sphere/Capsule/Cylinder/Plane/Quad) to spawn a preconfigured mesh
    with collider. Transform options set the initial pose; each takes three
    floats (X Y Z).

    Examples:
        u gameobject create -n Empty
        u gameobject create -n Wall -p Cube --position 0 0 5 --scale 10 2 1
        u gameobject create -n Floor -p Plane --rotation 0 0 0
    """
    context: CLIContext = ctx.obj
    result = context.client.gameobject.create(
        name=name,
        primitive_type=primitive,
        parent=parent,
        parent_id=parent_id,
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
    """Update a GameObject's position, rotation, and/or scale.

    Only the Transform options you pass are modified; the rest stay unchanged.
    Rotation is Euler angles in degrees.

    Examples:
        u gameobject modify -n Player --position 1 0 -3
        u gameobject modify --id 12345 --rotation 0 90 0 --scale 2 2 2
    """
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
    """Enable or disable a GameObject (equivalent to the Inspector's top-left toggle).

    Use --no-active to disable. The default --active enables the object.

    Examples:
        u gameobject active -n HUD --no-active
        u gameobject active --id 12345 --active
    """
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
    """Destroy a GameObject from the active scene.

    Examples:
        u gameobject delete -n TempSpawn
        u gameobject delete --id 12345
    """
    context: CLIContext = ctx.obj

    if not name and id is None:
        _exit_usage("--name or --id required", "u gameobject delete")

    result = context.client.gameobject.delete(name=name, instance_id=id)
    print_success(result.get("message", "GameObject deleted"))
