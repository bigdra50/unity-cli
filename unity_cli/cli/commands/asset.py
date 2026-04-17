"""Asset commands: prefab, scriptable-object, info, deps, refs."""

from __future__ import annotations

from typing import Annotated

import typer

from unity_cli.cli.context import CLIContext
from unity_cli.cli.helpers import _exit_usage, _should_json, handle_cli_errors
from unity_cli.cli.output import is_no_color, print_json, print_key_value, print_line, print_plain_table, print_success

asset_app = typer.Typer(
    help=(
        "Create and inspect project assets (Prefabs, ScriptableObjects) and explore\n"
        "dependency graphs via AssetDatabase.\n\n"
        "Commands:\n"
        "  prefab / scriptable-object  Create new asset files from scene objects or types\n"
        "  info                        Show asset GUID, type, importer info\n"
        "  deps                        What an asset depends on (textures, meshes, ...)\n"
        "  refs                        What depends on this asset (reverse lookup)"
    )
)


@asset_app.command("prefab")
@handle_cli_errors
def asset_prefab(
    ctx: typer.Context,
    path: Annotated[str, typer.Option("--path", "-p", help="Output path (e.g., Assets/Prefabs/My.prefab)")],
    source: Annotated[str | None, typer.Option("--source", "-s", help="Source GameObject name")] = None,
    source_id: Annotated[int | None, typer.Option("--source-id", help="Source GameObject instance ID")] = None,
) -> None:
    """Save a scene GameObject (and its children) as a Prefab asset.

    Examples:
        u asset prefab -s Player -p Assets/Prefabs/Player.prefab
        u asset prefab --source-id 12345 -p Assets/Prefabs/Enemy.prefab
    """
    context: CLIContext = ctx.obj

    if not source and source_id is None:
        _exit_usage("--source or --source-id required", "u asset prefab")

    result = context.client.asset.create_prefab(
        path=path,
        source=source,
        source_id=source_id,
    )
    print_success(result.get("message", f"Prefab created: {path}"))


@asset_app.command("scriptable-object")
@handle_cli_errors
def asset_scriptable_object(
    ctx: typer.Context,
    type_name: Annotated[str, typer.Option("--type", "-T", help="ScriptableObject type name")],
    path: Annotated[str, typer.Option("--path", "-p", help="Output path (e.g., Assets/Data/My.asset)")],
) -> None:
    """Instantiate a ScriptableObject-derived type as a new .asset file.

    --type takes the concrete class name (short or fully-qualified). The type
    must derive from UnityEngine.ScriptableObject and be reachable at runtime.

    Example:
        u asset scriptable-object -T GameConfig -p Assets/Data/GameConfig.asset
    """
    context: CLIContext = ctx.obj
    result = context.client.asset.create_scriptable_object(
        type_name=type_name,
        path=path,
    )
    print_success(result.get("message", f"ScriptableObject created: {path}"))


@asset_app.command("info")
@handle_cli_errors
def asset_info(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Asset path")],
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Show AssetDatabase metadata for a project asset (GUID, type, importer).

    Example:
        u asset info Assets/Prefabs/Player.prefab
    """
    context: CLIContext = ctx.obj
    result = context.client.asset.info(path=path)
    if _should_json(context, json_flag):
        print_json(result, None)
    else:
        print_key_value(result, path)


@asset_app.command("deps")
@handle_cli_errors
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
    """List assets that the given asset references (forward dependency graph).

    Recursive by default (-R for direct deps only).

    Example:
        u asset deps Assets/Scenes/Main.unity
        u asset deps Assets/Prefabs/Player.prefab -R
    """
    context: CLIContext = ctx.obj
    result = context.client.asset.deps(path=path, recursive=recursive)
    if _should_json(context, json_flag):
        print_json(result)
    else:
        deps = result.get("dependencies", [])
        if is_no_color():
            rows = [[dep.get("path", ""), dep.get("type", "")] for dep in deps]
            print_plain_table(["Path", "Type"], rows, header=False)
        else:
            count = result.get("count", len(deps))
            print_line(f"[bold]Dependencies for {path}[/bold] ({count})")
            if result.get("recursive"):
                print_line("[dim](recursive)[/dim]")
            print_line("")
            for dep in deps:
                print_line(f"  {dep.get('path')}")
                print_line(f"    [dim]type: {dep.get('type')}[/dim]")


@asset_app.command("refs")
@handle_cli_errors
def asset_refs(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Asset path")],
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Reverse lookup: find every asset that references the given asset.

    Useful before deleting/renaming to see where a texture, material, or
    ScriptableObject is wired in.

    Example:
        u asset refs Assets/Materials/Wood.mat
    """
    context: CLIContext = ctx.obj
    result = context.client.asset.refs(path=path)
    if _should_json(context, json_flag):
        print_json(result)
    else:
        refs = result.get("referencers", [])
        if is_no_color():
            rows = [[ref.get("path", ""), ref.get("type", "")] for ref in refs]
            print_plain_table(["Path", "Type"], rows, header=False)
        else:
            count = result.get("count", len(refs))
            print_line(f"[bold]Referencers of {path}[/bold] ({count})")
            print_line("")
            if count == 0:
                print_line("[dim]No references found[/dim]")
            else:
                for ref in refs:
                    print_line(f"  {ref.get('path')}")
                    print_line(f"    [dim]type: {ref.get('type')}[/dim]")
