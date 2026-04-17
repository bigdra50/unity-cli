"""Editor management commands (via Hub): list, install."""

from __future__ import annotations

from typing import Annotated

import typer

from unity_cli.cli.context import CLIContext
from unity_cli.cli.helpers import _handle_error, _should_json
from unity_cli.cli.output import _print_plain_table, get_console, is_no_color, print_json, print_line, print_success

editor_app = typer.Typer(
    help=(
        "Manage Unity Editor installations via Unity Hub CLI (no Relay required).\n\n"
        "Lists locally installed editors (by scanning Hub's config + common install\n"
        "paths) and invokes Hub's CLI to install new versions with optional modules.\n"
        "Pairs with 'u open <project>' which auto-picks the right editor for a project."
    )
)


@editor_app.command("list")
def editor_list(
    ctx: typer.Context,
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """List every Unity Editor installed on this machine (version + path).

    Scans Unity Hub's config and standard install locations.
    """
    context: CLIContext = ctx.obj
    from unity_cli.hub.paths import get_installed_editors

    editors = get_installed_editors()

    if _should_json(context, json_flag):
        data = [{"version": e.version, "path": str(e.path)} for e in editors]
        print_json(data)
    else:
        if not editors:
            print_line("[dim]No Unity editors found[/dim]")
            return

        if is_no_color():
            rows = [[editor.version, str(editor.path)] for editor in editors]
            _print_plain_table(["Version", "Path"], rows, f"Installed Editors ({len(editors)})")
        else:
            from rich.table import Table

            table = Table(title=f"Installed Editors ({len(editors)})")
            table.add_column("Version", style="cyan")
            table.add_column("Path", style="dim")
            for editor in editors:
                table.add_row(editor.version, str(editor.path))
            get_console().print(table)


@editor_app.command("install")
def editor_install(
    version: Annotated[str, typer.Argument(help="Unity version to install")],
    modules: Annotated[
        list[str] | None,
        typer.Option("--modules", "-m", help="Modules to install"),
    ] = None,
    changeset: Annotated[
        str | None,
        typer.Option("--changeset", "-c", help="Changeset for non-release versions"),
    ] = None,
) -> None:
    """Install a Unity Editor version through Unity Hub's CLI.

    VERSION accepts release tags like '2022.3.10f1', '6000.0.23f1', or beta/alpha
    tags paired with --changeset. --modules takes Unity platform/module IDs
    (android, ios, webgl, mac-il2cpp, linux-il2cpp, windows-il2cpp, ...).

    Examples:
        u editor install 2022.3.10f1
        u editor install 2022.3.10f1 -m android -m ios
        u editor install 6000.0.1a14 --changeset abcdef123456
    """
    from unity_cli.exceptions import HubError
    from unity_cli.hub.hub_cli import HubCLI

    try:
        hub = HubCLI()
        hub.install_editor(version=version, modules=modules, changeset=changeset)
        print_success(f"Installed Unity {version}")
        if modules:
            print_success(f"With modules: {', '.join(modules)}")
    except HubError as e:
        _handle_error(e)
