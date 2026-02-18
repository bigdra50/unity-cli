"""Package Manager commands: list, add, remove."""

from __future__ import annotations

from typing import Annotated

import typer

from unity_cli.cli.context import CLIContext
from unity_cli.cli.helpers import _handle_error, _should_json
from unity_cli.cli.output import _print_plain_table, get_console, is_no_color, print_json, print_success
from unity_cli.exceptions import UnityCLIError

package_app = typer.Typer(help="Package Manager commands (via Relay)")


@package_app.command("list")
def package_list(
    ctx: typer.Context,
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """List installed packages."""
    context: CLIContext = ctx.obj
    try:
        result = context.client.package.list()
        if _should_json(context, json_flag):
            print_json(result)
        else:
            packages = result.get("packages", [])

            if is_no_color():
                rows = [
                    [pkg.get("name", ""), pkg.get("version", ""), pkg.get("displayName", ""), pkg.get("source", "")]
                    for pkg in packages
                ]
                _print_plain_table(["Name", "Version", "Display Name", "Source"], rows, f"Packages ({len(packages)})")
            else:
                from rich.table import Table

                table = Table(title=f"Packages ({len(packages)})")
                table.add_column("Name", style="cyan")
                table.add_column("Version")
                table.add_column("Display Name")
                table.add_column("Source")
                for pkg in packages:
                    table.add_row(
                        pkg.get("name", ""),
                        pkg.get("version", ""),
                        pkg.get("displayName", ""),
                        pkg.get("source", ""),
                    )
                get_console().print(table)
    except UnityCLIError as e:
        _handle_error(e)


@package_app.command("add")
def package_add(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Package ID (e.g., com.unity.textmeshpro@3.0.6)")],
) -> None:
    """Add a package."""
    context: CLIContext = ctx.obj
    try:
        result = context.client.package.add(name)
        print_success(result.get("message", f"Package added: {name}"))
    except UnityCLIError as e:
        _handle_error(e)


@package_app.command("remove")
def package_remove(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Package name (e.g., com.unity.textmeshpro)")],
) -> None:
    """Remove a package."""
    context: CLIContext = ctx.obj
    try:
        result = context.client.package.remove(name)
        print_success(result.get("message", f"Package removed: {name}"))
    except UnityCLIError as e:
        _handle_error(e)
