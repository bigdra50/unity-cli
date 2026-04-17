"""Package Manager commands: list, add, remove."""

from __future__ import annotations

from typing import Annotated

import typer

from unity_cli.cli.context import CLIContext
from unity_cli.cli.helpers import _handle_error, _should_json
from unity_cli.cli.output import _print_plain_table, get_console, is_no_color, print_json, print_success
from unity_cli.exceptions import UnityCLIError

package_app = typer.Typer(
    help=(
        "Query and manage UPM packages in the open Unity project (Package Manager).\n\n"
        "Runs through UnityEditor.PackageManager.Client inside the Editor, so changes\n"
        "touch Packages/manifest.json and trigger a domain reload — the CLI waits for\n"
        "that reload to complete before returning."
    )
)


@package_app.command("list")
def package_list(
    ctx: typer.Context,
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """List packages currently installed (registry, git, local, built-in)."""
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
    name: Annotated[
        str,
        typer.Argument(
            help=(
                "Package identifier. Accepts the same forms as UPM: "
                "'com.unity.textmeshpro@3.0.6' (registry), "
                "'https://github.com/org/repo.git' (git), "
                "'file:../LocalPackage' (local path)."
            )
        ),
    ],
) -> None:
    """Install a package via the Package Manager (same as Window > Package Manager > Add).

    Examples:
        u package add com.unity.textmeshpro@3.0.6
        u package add https://github.com/cysharp/UniTask.git?path=src/UniTask/Assets/Plugins/UniTask
        u package add file:../Shared/MyLocalPackage
    """
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
    """Uninstall a package (removes the entry from Packages/manifest.json).

    Example:
        u package remove com.unity.textmeshpro
    """
    context: CLIContext = ctx.obj
    try:
        result = context.client.package.remove(name)
        print_success(result.get("message", f"Package removed: {name}"))
    except UnityCLIError as e:
        _handle_error(e)
