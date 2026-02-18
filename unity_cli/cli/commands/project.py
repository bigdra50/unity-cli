"""Project information commands (file-based, no Relay required)."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import typer

from unity_cli.cli.context import CLIContext
from unity_cli.cli.exit_codes import ExitCode
from unity_cli.cli.helpers import _handle_error, _should_json
from unity_cli.cli.output import _print_plain_table, get_console, is_no_color, print_error, print_json, print_line

project_app = typer.Typer(help="Project information (file-based, no Relay required)")


@project_app.command("info")
def project_info(
    ctx: typer.Context,
    path: Annotated[
        Path,
        typer.Argument(help="Unity project path"),
    ] = Path("."),
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Show project information parsed from files.

    Displays: Unity version, product name, company, build scenes, packages.
    No Relay Server connection required.
    """
    from unity_cli.exceptions import ProjectError
    from unity_cli.hub.project import ProjectInfo

    context: CLIContext = ctx.obj
    try:
        info = ProjectInfo.from_path(path)

        if _should_json(context, json_flag):
            print_json(info.to_dict())
        else:
            _print_project_info(info)

    except ProjectError as e:
        _handle_error(e)


def _print_project_info(info: Any) -> None:
    from rich.panel import Panel

    if is_no_color():
        print_line(f"{info.settings.product_name} ({info.path})")
    else:
        get_console().print(Panel(f"[bold]{info.settings.product_name}[/bold]", subtitle=str(info.path)))
    print_line(f"Company: {info.settings.company_name}")
    print_line(f"Version: {info.settings.version}")
    print_line(f"Unity: {info.unity_version.version}")
    if info.unity_version.revision:
        print_line(f"Revision: [dim]{info.unity_version.revision}[/dim]")
    print_line(f"Screen: {info.settings.default_screen_width}x{info.settings.default_screen_height}")
    print_line("")

    if info.build_settings.scenes:
        _print_build_scenes_table(info.build_settings.scenes)
        print_line("")

    if info.packages.dependencies:
        _print_packages_info_table(info.packages.dependencies)


def _print_build_scenes_table(scenes: list[Any]) -> None:
    if is_no_color():
        rows = [[str(i), s.path, "yes" if s.enabled else "no"] for i, s in enumerate(scenes)]
        _print_plain_table(["#", "Path", "Enabled"], rows, "Build Scenes")
    else:
        from rich.table import Table

        t = Table(title="Build Scenes")
        t.add_column("#", style="dim")
        t.add_column("Path")
        t.add_column("Enabled")
        for i, s in enumerate(scenes):
            t.add_row(str(i), s.path, "[green]✓[/green]" if s.enabled else "[red]✗[/red]")
        get_console().print(t)


def _print_packages_info_table(deps: list[Any]) -> None:
    if is_no_color():
        rows = [[p.name, p.version, "local" if p.is_local else ""] for p in deps]
        _print_plain_table(["Name", "Version", "Local"], rows, f"Packages ({len(deps)})")
    else:
        from rich.table import Table

        t = Table(title=f"Packages ({len(deps)})")
        t.add_column("Name", style="cyan")
        t.add_column("Version")
        t.add_column("Local")
        for p in deps:
            t.add_row(p.name, p.version, "[yellow]local[/yellow]" if p.is_local else "")
        get_console().print(t)


@project_app.command("version")
def project_version(
    ctx: typer.Context,
    path: Annotated[
        Path,
        typer.Argument(help="Unity project path"),
    ] = Path("."),
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Show Unity version for project."""
    from unity_cli.exceptions import ProjectVersionError
    from unity_cli.hub.project import ProjectVersion

    context: CLIContext = ctx.obj
    try:
        version = ProjectVersion.from_file(path)

        if _should_json(context, json_flag):
            print_json({"version": version.version, "revision": version.revision})
        else:
            print_line(f"Unity: [cyan]{version.version}[/cyan]")
            if version.revision:
                print_line(f"Revision: [dim]{version.revision}[/dim]")

    except ProjectVersionError as e:
        _handle_error(e)


@project_app.command("packages")
def project_packages(
    ctx: typer.Context,
    path: Annotated[
        Path,
        typer.Argument(help="Unity project path"),
    ] = Path("."),
    include_modules: Annotated[
        bool,
        typer.Option("--include-modules", help="Include Unity built-in modules"),
    ] = False,
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """List installed packages from manifest.json."""
    context: CLIContext = ctx.obj
    from unity_cli.hub.project import is_unity_project

    path = path.resolve()

    if not is_unity_project(path):
        print_error(f"Not a valid Unity project: {path}", "INVALID_PROJECT")
        raise typer.Exit(ExitCode.USAGE_ERROR) from None

    manifest_file = path / "Packages/manifest.json"
    if not manifest_file.exists():
        print_error("manifest.json not found", "MANIFEST_NOT_FOUND")
        raise typer.Exit(ExitCode.USAGE_ERROR) from None

    import json

    deps = json.loads(manifest_file.read_text(encoding="utf-8")).get("dependencies", {})
    packages = [
        {"name": n, "version": v, "local": v.startswith("file:")}
        for n, v in sorted(deps.items())
        if include_modules or not n.startswith("com.unity.modules.")
    ]

    if _should_json(context, json_flag):
        print_json(packages)
    else:
        _print_manifest_packages(packages)


def _print_manifest_packages(packages: list[dict[str, Any]]) -> None:
    title = f"Packages ({len(packages)})"
    if is_no_color():
        rows = [[pkg["name"], pkg["version"]] for pkg in packages]
        _print_plain_table(["Name", "Version"], rows, title)
    else:
        from rich.table import Table

        table = Table(title=title)
        table.add_column("Name", style="cyan")
        table.add_column("Version")
        for pkg in packages:
            v = f"[yellow]{pkg['version']}[/yellow]" if pkg["local"] else pkg["version"]
            table.add_row(pkg["name"], v)
        get_console().print(table)


@project_app.command("tags")
def project_tags(
    ctx: typer.Context,
    path: Annotated[
        Path,
        typer.Argument(help="Unity project path"),
    ] = Path("."),
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Show tags, layers, and sorting layers."""
    context: CLIContext = ctx.obj
    from unity_cli.hub.project import TagLayerSettings, is_unity_project

    path = path.resolve()

    if not is_unity_project(path):
        print_error(f"Not a valid Unity project: {path}", "INVALID_PROJECT")
        raise typer.Exit(ExitCode.USAGE_ERROR) from None

    settings = TagLayerSettings.from_file(path)

    if _should_json(context, json_flag):
        print_json(
            {
                "tags": settings.tags,
                "layers": [{"index": i, "name": n} for i, n in settings.layers],
                "sorting_layers": settings.sorting_layers,
            }
        )
    else:
        _print_tag_layer_settings(settings)


def _print_tag_layer_settings(settings: Any) -> None:
    if settings.tags:
        print_line("[bold]Tags:[/bold]")
        for tag in settings.tags:
            print_line(f"  - {tag}")
    else:
        print_line("[dim]No custom tags[/dim]")
    print_line("")

    if is_no_color():
        rows = [[str(idx), name] for idx, name in settings.layers]
        _print_plain_table(["#", "Name"], rows, "Layers")
    else:
        from rich.table import Table

        layer_table = Table(title="Layers")
        layer_table.add_column("#", style="dim", width=3)
        layer_table.add_column("Name", style="cyan")
        for idx, name in settings.layers:
            layer_table.add_row(str(idx), name)
        get_console().print(layer_table)
    print_line("")

    if settings.sorting_layers:
        print_line("[bold]Sorting Layers:[/bold]")
        for i, layer in enumerate(settings.sorting_layers):
            print_line(f"  {i}: {layer}")


@project_app.command("quality")
def project_quality(
    ctx: typer.Context,
    path: Annotated[
        Path,
        typer.Argument(help="Unity project path"),
    ] = Path("."),
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Show quality settings."""
    context: CLIContext = ctx.obj
    from unity_cli.hub.project import QualitySettings, is_unity_project

    path = path.resolve()

    if not is_unity_project(path):
        print_error(f"Not a valid Unity project: {path}", "INVALID_PROJECT")
        raise typer.Exit(ExitCode.USAGE_ERROR) from None

    settings = QualitySettings.from_file(path)

    if _should_json(context, json_flag):
        print_json(
            {
                "current_quality": settings.current_quality,
                "levels": [
                    {
                        "name": lvl.name,
                        "shadow_resolution": lvl.shadow_resolution,
                        "shadow_distance": lvl.shadow_distance,
                        "vsync_count": lvl.vsync_count,
                        "lod_bias": lvl.lod_bias,
                        "anti_aliasing": lvl.anti_aliasing,
                    }
                    for lvl in settings.levels
                ],
            }
        )
    else:
        title = f"Quality Levels (current: {settings.current_quality})"
        headers = ["#", "Name", "Shadow Res", "Shadow Dist", "VSync", "LOD Bias", "AA"]

        if is_no_color():
            rows = [
                [
                    f"{'>' if i == settings.current_quality else ' '}{i}",
                    lvl.name,
                    str(lvl.shadow_resolution),
                    str(lvl.shadow_distance),
                    str(lvl.vsync_count),
                    str(lvl.lod_bias),
                    str(lvl.anti_aliasing),
                ]
                for i, lvl in enumerate(settings.levels)
            ]
            _print_plain_table(headers, rows, title)
        else:
            from rich.table import Table

            table = Table(title=title)
            table.add_column("#", style="dim", width=3)
            table.add_column("Name", style="cyan")
            table.add_column("Shadow Res")
            table.add_column("Shadow Dist")
            table.add_column("VSync")
            table.add_column("LOD Bias")
            table.add_column("AA")
            for i, lvl in enumerate(settings.levels):
                marker = "[green]►[/green]" if i == settings.current_quality else " "
                table.add_row(
                    f"{marker}{i}",
                    lvl.name,
                    str(lvl.shadow_resolution),
                    str(lvl.shadow_distance),
                    str(lvl.vsync_count),
                    str(lvl.lod_bias),
                    str(lvl.anti_aliasing),
                )
            get_console().print(table)


@project_app.command("assemblies")
def project_assemblies(
    ctx: typer.Context,
    path: Annotated[
        Path,
        typer.Argument(help="Unity project path"),
    ] = Path("."),
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """List Assembly Definitions (.asmdef) in Assets/."""
    context: CLIContext = ctx.obj
    from unity_cli.hub.project import find_assembly_definitions, is_unity_project

    path = path.resolve()

    if not is_unity_project(path):
        print_error(f"Not a valid Unity project: {path}", "INVALID_PROJECT")
        raise typer.Exit(ExitCode.USAGE_ERROR) from None

    assemblies = find_assembly_definitions(path)

    if _should_json(context, json_flag):
        print_json(
            [
                {
                    "name": asm.name,
                    "path": str(asm.path.relative_to(path)),
                    "references": asm.references,
                    "include_platforms": asm.include_platforms,
                    "exclude_platforms": asm.exclude_platforms,
                    "allow_unsafe": asm.allow_unsafe,
                    "auto_referenced": asm.auto_referenced,
                }
                for asm in assemblies
            ]
        )
    else:
        if not assemblies:
            print_line("[dim]No Assembly Definitions found in Assets/[/dim]")
            return

        if is_no_color():
            rows = [
                [asm.name, str(asm.path.relative_to(path)), str(len(asm.references)), "yes" if asm.allow_unsafe else ""]
                for asm in assemblies
            ]
            _print_plain_table(["Name", "Path", "Refs", "Unsafe"], rows, f"Assembly Definitions ({len(assemblies)})")
        else:
            from rich.table import Table

            table = Table(title=f"Assembly Definitions ({len(assemblies)})")
            table.add_column("Name", style="cyan")
            table.add_column("Path", style="dim")
            table.add_column("Refs", justify="right")
            table.add_column("Unsafe")
            for asm in assemblies:
                rel_path = asm.path.relative_to(path)
                unsafe = "[yellow]✓[/yellow]" if asm.allow_unsafe else ""
                table.add_row(asm.name, str(rel_path), str(len(asm.references)), unsafe)
            get_console().print(table)
