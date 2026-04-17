"""Configuration commands: show, init."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from unity_cli.cli.context import CLIContext
from unity_cli.cli.exit_codes import ExitCode
from unity_cli.cli.helpers import _should_json
from unity_cli.cli.output import print_error, print_json, print_line, print_success
from unity_cli.config import CONFIG_FILE_NAME, UnityCLIConfig

config_app = typer.Typer(
    help=(
        "Inspect or generate the unity-cli config file (.unity-cli.toml).\n\n"
        "Stores default relay host/port, timeout, and the preferred Unity instance\n"
        "so you don't need to repeat --relay-* or -i on every invocation. Looked up\n"
        "from the current directory upward, similar to .editorconfig."
    )
)


@config_app.command("show")
def config_show(
    ctx: typer.Context,
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Print the resolved config (from file + env vars + CLI flags) and its source path."""
    context: CLIContext = ctx.obj
    config_file = UnityCLIConfig._find_config_file()

    if _should_json(context, json_flag):
        # JSON mode
        data = {
            "config_file": str(config_file) if config_file else None,
            "relay_host": context.config.relay_host,
            "relay_port": context.config.relay_port,
            "timeout": context.config.timeout,
            "instance": context.config.instance,
        }
        print_json(data, None)
    else:
        print_line("[bold]=== Unity CLI Configuration ===[/bold]")
        print_line(f"Config file: {config_file or '[dim]Not found (using defaults)[/dim]'}")
        print_line(f"Relay host: {context.config.relay_host}")
        print_line(f"Relay port: {context.config.relay_port}")
        print_line(f"Timeout: {context.config.timeout}s")
        print_line(f"Instance: {context.config.instance or '[dim](default)[/dim]'}")


@config_app.command("init")
def config_init(
    ctx: typer.Context,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output path"),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite existing config"),
    ] = False,
) -> None:
    """Write a default .unity-cli.toml into the current directory (edit to taste).

    Use --output to pick a different path, --force to overwrite an existing file.
    """
    output_path = output or Path(CONFIG_FILE_NAME)

    if output_path.exists() and not force:
        print_error(f"{output_path} already exists. Use --force to overwrite.")
        raise typer.Exit(ExitCode.USAGE_ERROR) from None

    default_config = UnityCLIConfig()
    output_path.write_text(default_config.to_toml())
    print_success(f"Created {output_path}")
