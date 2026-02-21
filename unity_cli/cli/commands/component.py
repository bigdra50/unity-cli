"""Component commands: list, inspect, add, modify, remove."""

from __future__ import annotations

from typing import Annotated

import typer

from unity_cli.cli.context import CLIContext
from unity_cli.cli.helpers import _exit_usage, _parse_cli_value, _should_json, handle_cli_errors
from unity_cli.cli.output import print_components_table, print_json, print_key_value, print_success

component_app = typer.Typer(help="Component commands")


@component_app.command("list")
@handle_cli_errors
def component_list(
    ctx: typer.Context,
    target: Annotated[str | None, typer.Option("--target", "-t", help="Target GameObject name")] = None,
    target_id: Annotated[int | None, typer.Option("--target-id", help="Target GameObject ID")] = None,
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """List components on a GameObject."""
    context: CLIContext = ctx.obj

    if not target and target_id is None:
        _exit_usage("--target or --target-id required", "u component list")

    result = context.client.component.list(target=target, target_id=target_id)
    if _should_json(context, json_flag):
        print_json(result)
    else:
        print_components_table(result.get("components", []))


@component_app.command("inspect")
@handle_cli_errors
def component_inspect(
    ctx: typer.Context,
    component_type: Annotated[str, typer.Option("--type", "-T", help="Component type name")],
    target: Annotated[str | None, typer.Option("--target", "-t", help="Target GameObject name")] = None,
    target_id: Annotated[int | None, typer.Option("--target-id", help="Target GameObject ID")] = None,
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Inspect component properties."""
    context: CLIContext = ctx.obj

    if not target and target_id is None:
        _exit_usage("--target or --target-id required", "u component inspect")

    result = context.client.component.inspect(
        target=target,
        target_id=target_id,
        component_type=component_type,
    )
    if _should_json(context, json_flag):
        print_json(result, None)
    else:
        print_key_value(result, component_type)


@component_app.command("add")
@handle_cli_errors
def component_add(
    ctx: typer.Context,
    component_type: Annotated[str, typer.Option("--type", "-T", help="Component type name to add")],
    target: Annotated[str | None, typer.Option("--target", "-t", help="Target GameObject name")] = None,
    target_id: Annotated[int | None, typer.Option("--target-id", help="Target GameObject ID")] = None,
) -> None:
    """Add a component to a GameObject."""
    context: CLIContext = ctx.obj

    if not target and target_id is None:
        _exit_usage("--target or --target-id required", "u component add")

    result = context.client.component.add(
        target=target,
        target_id=target_id,
        component_type=component_type,
    )
    print_success(result.get("message", "Component added"))


@component_app.command("modify")
@handle_cli_errors
def component_modify(
    ctx: typer.Context,
    component_type: Annotated[str, typer.Option("--type", "-T", help="Component type name")],
    prop: Annotated[str, typer.Option("--prop", "-p", help="Property name to modify")],
    value: Annotated[
        str,
        typer.Option("--value", "-v", help="New value (auto-parsed: numbers, booleans, JSON arrays/objects)"),
    ],
    target: Annotated[str | None, typer.Option("--target", "-t", help="Target GameObject name")] = None,
    target_id: Annotated[int | None, typer.Option("--target-id", help="Target GameObject ID")] = None,
) -> None:
    """Modify a component property.

    Values are auto-parsed: integers, floats, booleans (true/false),
    JSON arrays ([1,2,3]), and JSON objects ({"r":1,"g":0,"b":0}) are
    converted to their appropriate types. Everything else is sent as a string.

    Examples:
        u component modify -t "Main Camera" -T Camera --prop fieldOfView --value 90
        u component modify -t "Cube" -T Transform --prop m_LocalPosition --value "[1,2,3]"
    """
    context: CLIContext = ctx.obj

    if not target and target_id is None:
        _exit_usage("--target or --target-id required", "u component modify")

    parsed_value = _parse_cli_value(value)

    result = context.client.component.modify(
        target=target,
        target_id=target_id,
        component_type=component_type,
        prop=prop,
        value=parsed_value,
    )
    print_success(result.get("message", "Property modified"))


@component_app.command("remove")
@handle_cli_errors
def component_remove(
    ctx: typer.Context,
    component_type: Annotated[str, typer.Option("--type", "-T", help="Component type name to remove")],
    target: Annotated[str | None, typer.Option("--target", "-t", help="Target GameObject name")] = None,
    target_id: Annotated[int | None, typer.Option("--target-id", help="Target GameObject ID")] = None,
) -> None:
    """Remove a component from a GameObject."""
    context: CLIContext = ctx.obj

    if not target and target_id is None:
        _exit_usage("--target or --target-id required", "u component remove")

    result = context.client.component.remove(
        target=target,
        target_id=target_id,
        component_type=component_type,
    )
    print_success(result.get("message", "Component removed"))
