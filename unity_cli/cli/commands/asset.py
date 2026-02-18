"""Asset commands: prefab, scriptable-object, info, deps, refs."""

from __future__ import annotations

from typing import Annotated

import typer

from unity_cli.cli.context import CLIContext
from unity_cli.cli.helpers import _exit_usage, _handle_error, _should_json
from unity_cli.cli.output import print_json, print_key_value, print_line, print_success
from unity_cli.exceptions import UnityCLIError

asset_app = typer.Typer(help="Asset commands (Prefab, ScriptableObject)")


@asset_app.command("prefab")
def asset_prefab(
    ctx: typer.Context,
    path: Annotated[str, typer.Option("--path", "-p", help="Output path (e.g., Assets/Prefabs/My.prefab)")],
    source: Annotated[str | None, typer.Option("--source", "-s", help="Source GameObject name")] = None,
    source_id: Annotated[int | None, typer.Option("--source-id", help="Source GameObject instance ID")] = None,
) -> None:
    """Create a Prefab from a GameObject."""
    context: CLIContext = ctx.obj

    if not source and source_id is None:
        _exit_usage("--source or --source-id required", "u asset prefab")

    try:
        result = context.client.asset.create_prefab(
            path=path,
            source=source,
            source_id=source_id,
        )
        print_success(result.get("message", f"Prefab created: {path}"))
    except UnityCLIError as e:
        _handle_error(e)


@asset_app.command("scriptable-object")
def asset_scriptable_object(
    ctx: typer.Context,
    type_name: Annotated[str, typer.Option("--type", "-T", help="ScriptableObject type name")],
    path: Annotated[str, typer.Option("--path", "-p", help="Output path (e.g., Assets/Data/My.asset)")],
) -> None:
    """Create a ScriptableObject asset."""
    context: CLIContext = ctx.obj
    try:
        result = context.client.asset.create_scriptable_object(
            type_name=type_name,
            path=path,
        )
        print_success(result.get("message", f"ScriptableObject created: {path}"))
    except UnityCLIError as e:
        _handle_error(e)


@asset_app.command("info")
def asset_info(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Asset path")],
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Get asset information."""
    context: CLIContext = ctx.obj
    try:
        result = context.client.asset.info(path=path)
        if _should_json(context, json_flag):
            print_json(result, None)
        else:
            print_key_value(result, path)
    except UnityCLIError as e:
        _handle_error(e)


@asset_app.command("deps")
def asset_deps(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Asset path")],
    recursive: Annotated[
        bool,
        typer.Option("--recursive/--no-recursive", "-r/-R", help="Include indirect dependencies"),
    ] = True,
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Get asset dependencies (what this asset depends on)."""
    context: CLIContext = ctx.obj
    try:
        result = context.client.asset.deps(path=path, recursive=recursive)
        if _should_json(context, json_flag):
            print_json(result)
        else:
            deps = result.get("dependencies", [])
            count = result.get("count", len(deps))
            print_line(f"[bold]Dependencies for {path}[/bold] ({count})")
            if result.get("recursive"):
                print_line("[dim](recursive)[/dim]")
            print_line("")
            for dep in deps:
                print_line(f"  {dep.get('path')}")
                print_line(f"    [dim]type: {dep.get('type')}[/dim]")
    except UnityCLIError as e:
        _handle_error(e)


@asset_app.command("refs")
def asset_refs(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Asset path")],
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Get asset referencers (what depends on this asset)."""
    context: CLIContext = ctx.obj
    try:
        result = context.client.asset.refs(path=path)
        if _should_json(context, json_flag):
            print_json(result)
        else:
            refs = result.get("referencers", [])
            count = result.get("count", len(refs))
            print_line(f"[bold]Referencers of {path}[/bold] ({count})")
            print_line("")
            if count == 0:
                print_line("[dim]No references found[/dim]")
            else:
                for ref in refs:
                    print_line(f"  {ref.get('path')}")
                    print_line(f"    [dim]type: {ref.get('type')}[/dim]")
    except UnityCLIError as e:
        _handle_error(e)
