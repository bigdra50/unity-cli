"""Menu item commands: exec, list, context."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.markup import escape

from unity_cli.cli.context import CLIContext
from unity_cli.cli.exit_codes import ExitCode
from unity_cli.cli.helpers import _handle_error, _should_json
from unity_cli.cli.output import is_no_color, print_error, print_json, print_line, print_plain_item, print_success
from unity_cli.exceptions import UnityCLIError

menu_app = typer.Typer(
    help=(
        "Invoke Unity menu items and [ContextMenu] methods.\n\n"
        "Covers any MenuItem registered with Unity's menu bar — Unity's built-in menus\n"
        "(Edit/Play, Assets/Refresh, Window/...) AND custom editor tools you or a\n"
        'package register via [MenuItem("Tools/MyTool")]. This is the go-to way to\n'
        "trigger editor workflows that have no dedicated CLI command."
    )
)


@menu_app.command("exec")
def menu_exec(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Menu item path (e.g., 'Edit/Play', 'Tools/MyCustomAction')")],
) -> None:
    """Execute any Unity menu item by its menu-bar path.

    Works with:
      - Built-in menus: 'Edit/Play', 'File/Save', 'Assets/Refresh'
      - Package menus:  'Window/Package Manager', 'Window/Analysis/Profiler'
      - Custom tools:   any [MenuItem("Path/To/Action")] defined in your project

    Use 'u menu list' (optionally with --filter) to discover available menu paths.

    Examples:
        u menu exec 'Edit/Play'
        u menu exec 'Assets/Refresh'
        u menu exec 'Window/Rendering/Lighting'
        u menu exec 'Tools/RegenerateData'          # custom [MenuItem]
    """
    context: CLIContext = ctx.obj
    try:
        result = context.client.menu.execute(path)
        if result.get("success"):
            print_success(result.get("message", f"Executed: {path}"))
        else:
            print_error(result.get("message", f"Failed: {path}"))
            raise typer.Exit(ExitCode.OPERATION_ERROR) from None
    except UnityCLIError as e:
        _handle_error(e)


@menu_app.command("list")
def menu_list(
    ctx: typer.Context,
    filter_text: Annotated[
        str | None,
        typer.Option("--filter", "-f", help="Filter menu items (case-insensitive)"),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", help="Maximum items to return"),
    ] = 100,
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """List Unity menu-bar entries (built-in + custom [MenuItem]).

    Useful for discovering which paths 'u menu exec' can invoke.

    Examples:
        u menu list                        # All menu items
        u menu list -f Tools               # Items containing 'Tools'
        u menu list -f "Window/Analysis"   # Narrow to a submenu
    """
    context: CLIContext = ctx.obj
    try:
        result = context.client.menu.list(filter_text=filter_text, limit=limit)
        if _should_json(context, json_flag):
            print_json(result)
        else:
            items = result.get("items", [])
            if is_no_color():
                for item in items:
                    path = item.get("path", str(item)) if isinstance(item, dict) else str(item)
                    print_plain_item(path)
            else:
                print_line(f"[bold]Menu Items ({len(items)})[/bold]")
                for item in items:
                    path = item.get("path", str(item)) if isinstance(item, dict) else str(item)
                    print_line(f"  {escape(path)}")
    except UnityCLIError as e:
        _handle_error(e)


@menu_app.command("context")
def menu_context(
    ctx: typer.Context,
    method: Annotated[str, typer.Argument(help="ContextMenu method name")],
    target: Annotated[
        str | None,
        typer.Option("--target", "-t", help="Target object path (hierarchy or asset)"),
    ] = None,
) -> None:
    """Invoke a [ContextMenu] method on a GameObject, Component, or Asset.

    Targets methods decorated with [ContextMenu("MethodName")] in MonoBehaviours
    or ScriptableObjects — equivalent to right-clicking the component header and
    selecting the entry. If --target is omitted, the current Selection is used.

    Examples:
        u menu context Reset                                 # On current selection
        u menu context Bake -t "Assets/Data/LightConfig.asset"
        u menu context Regenerate -t "Player"                # Hierarchy name
    """
    context: CLIContext = ctx.obj
    try:
        result = context.client.menu.context(method=method, target=target)
        print_success(result.get("message", f"Executed: {method}"))
    except UnityCLIError as e:
        _handle_error(e)
