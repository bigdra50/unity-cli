"""
Unity CLI - Typer Application
==============================

Assembly point: defines the main Typer app, global options callback,
and registers all command modules.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

# --- Top-level command imports ---
from unity_cli.cli.commands import (
    completion,
    editor_control,
    open_cmd,
    selection,
)
from unity_cli.cli.commands.asset import asset_app
from unity_cli.cli.commands.build import build_app
from unity_cli.cli.commands.component import component_app
from unity_cli.cli.commands.config import config_app

# --- Sub-app imports ---
from unity_cli.cli.commands.console import console_app
from unity_cli.cli.commands.editor_hub import editor_app
from unity_cli.cli.commands.gameobject import gameobject_app
from unity_cli.cli.commands.menu import menu_app
from unity_cli.cli.commands.package import package_app
from unity_cli.cli.commands.profiler import profiler_app
from unity_cli.cli.commands.project import project_app
from unity_cli.cli.commands.recorder import recorder_app
from unity_cli.cli.commands.scene import scene_app
from unity_cli.cli.commands.screenshot import screenshot
from unity_cli.cli.commands.tests import tests_app
from unity_cli.cli.commands.uitree import uitree_app
from unity_cli.cli.context import CLIContext, _on_retry_callback, _on_send_verbose
from unity_cli.cli.output import (
    OutputConfig,
    configure_output,
    resolve_output_mode,
    set_quiet,
)
from unity_cli.config import UnityCLIConfig

# =============================================================================
# Main Application
# =============================================================================

app = typer.Typer(
    name="unity-cli",
    help="Unity CLI - Control Unity Editor via Relay Server",
    no_args_is_help=True,
    rich_markup_mode="rich",
)


# =============================================================================
# Global Options Callback
# =============================================================================


@app.callback()
def main(
    ctx: typer.Context,
    relay_host: Annotated[
        str | None,
        typer.Option(
            "--relay-host",
            help="Relay server host",
            envvar="UNITY_RELAY_HOST",
        ),
    ] = None,
    relay_port: Annotated[
        int | None,
        typer.Option(
            "--relay-port",
            help="Relay server port",
            envvar="UNITY_RELAY_PORT",
        ),
    ] = None,
    instance: Annotated[
        str | None,
        typer.Option(
            "--instance",
            "-i",
            help="Target Unity instance (path, project name, or prefix)",
            envvar="UNITY_INSTANCE",
        ),
    ] = None,
    timeout: Annotated[
        float | None,
        typer.Option(
            "--timeout",
            "-t",
            help="Timeout in seconds",
        ),
    ] = None,
    pretty_flag: Annotated[
        bool | None,
        typer.Option(
            "--pretty/--no-pretty",
            help="Force pretty or plain output",
        ),
    ] = None,
    quiet: Annotated[
        bool,
        typer.Option(
            "--quiet",
            "-q",
            help="Suppress success messages (errors still go to stderr)",
            envvar="UNITY_CLI_QUIET",
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            help="Show request/response on stderr",
            envvar="UNITY_CLI_VERBOSE",
        ),
    ] = False,
) -> None:
    """Unity CLI - Control Unity Editor via Relay Server."""
    from unity_cli.client import UnityClient

    # Resolve output mode and configure consoles
    output_mode = resolve_output_mode(pretty_flag=pretty_flag)
    configure_output(output_mode)
    output_config = OutputConfig(mode=output_mode)
    set_quiet(quiet)

    # Load config from file
    config = UnityCLIConfig.load()

    # Override with CLI options
    if relay_host is not None:
        config.relay_host = relay_host
    if relay_port is not None:
        config.relay_port = relay_port
    if timeout is not None:
        config.timeout = timeout
    if instance is not None:
        resolved = Path(instance).resolve()
        config.instance = str(resolved) if resolved.is_dir() else instance

    # Create client with retry callback for CLI feedback
    client = UnityClient(
        relay_host=config.relay_host,
        relay_port=config.relay_port,
        timeout=config.timeout,
        instance=config.instance,
        timeout_ms=config.timeout_ms,
        retry_initial_ms=config.retry_initial_ms,
        retry_max_ms=config.retry_max_ms,
        retry_max_time_ms=config.retry_max_time_ms,
        on_retry=_on_retry_callback,
        on_send=_on_send_verbose if verbose else None,
    )

    # Store in context for sub-commands
    ctx.obj = CLIContext(
        config=config,
        client=client,
        output=output_config,
    )


# =============================================================================
# Register sub-apps (Typer groups)
# =============================================================================

app.add_typer(console_app, name="console")
app.add_typer(scene_app, name="scene")
app.add_typer(tests_app, name="tests")
app.add_typer(gameobject_app, name="gameobject")
app.add_typer(component_app, name="component")
app.add_typer(menu_app, name="menu")
app.add_typer(asset_app, name="asset")
app.add_typer(build_app, name="build")
app.add_typer(package_app, name="package")
app.add_typer(profiler_app, name="profiler")
app.add_typer(uitree_app, name="uitree")
app.add_typer(config_app, name="config")
app.add_typer(project_app, name="project")
app.add_typer(editor_app, name="editor")
app.command("screenshot")(screenshot)
app.add_typer(recorder_app, name="recorder")

# =============================================================================
# Register top-level commands
# =============================================================================

editor_control.register(app)
selection.register(app)
open_cmd.register(app)
completion.register(app)


# =============================================================================
# Entry Point
# =============================================================================


def cli_main() -> None:
    """CLI entry point."""
    app()


if __name__ == "__main__":
    cli_main()
