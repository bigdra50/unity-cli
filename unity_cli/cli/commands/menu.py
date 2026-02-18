"""Menu item commands: exec, list, context."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.markup import escape

from unity_cli.cli.context import CLIContext
from unity_cli.cli.exit_codes import ExitCode
from unity_cli.cli.helpers import _handle_error, _should_json
from unity_cli.cli.output import print_error, print_json, print_line, print_success
from unity_cli.exceptions import UnityCLIError

menu_app = typer.Typer(help="Menu item commands")


@menu_app.command("exec")
def menu_exec(
    ctx: typer.Context,
    path: Annotated[str, typer.Argument(help="Menu item path (e.g., 'Edit/Play')")],
) -> None:
    """Execute a Unity menu item."""
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
    """List available menu items."""
    context: CLIContext = ctx.obj
    try:
        result = context.client.menu.list(filter_text=filter_text, limit=limit)
        if _should_json(context, json_flag):
            print_json(result)
        else:
            items = result.get("items", [])
            print_line(f"[bold]Menu Items ({len(items)})[/bold]")
            for item in items:
                print_line(f"  {escape(str(item))}")
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
    """Execute a ContextMenu method on target object."""
    context: CLIContext = ctx.obj
    try:
        result = context.client.menu.context(method=method, target=target)
        print_success(result.get("message", f"Executed: {method}"))
    except UnityCLIError as e:
        _handle_error(e)
