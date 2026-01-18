"""
Unity CLI Package
==================

Control Unity Editor via TCP Relay Server.

Main exports:
    - UnityClient: Main client for interacting with Unity
    - UnityCLIConfig: Configuration management
    - Vector3, Color: Domain models
    - Exception classes: UnityCLIError, ConnectionError, etc.

Example:
    >>> from unity_cli import UnityClient
    >>> client = UnityClient()
    >>> client.editor.play()
"""

from unity_cli.client import UnityClient
from unity_cli.config import (
    CONFIG_FILE_NAME,
    DEFAULT_RELAY_HOST,
    DEFAULT_RELAY_PORT,
    DEFAULT_TIMEOUT_MS,
    HEADER_SIZE,
    MAX_PAYLOAD_BYTES,
    PROTOCOL_VERSION,
    VALID_LOG_TYPES,
    UnityCLIConfig,
)
from unity_cli.exceptions import (
    ConnectionError,
    InstanceError,
    ProtocolError,
    TimeoutError,
    UnityCLIError,
)
from unity_cli.models import Color, Vector3

__all__ = [
    # Client
    "UnityClient",
    # Config
    "UnityCLIConfig",
    "CONFIG_FILE_NAME",
    "DEFAULT_RELAY_HOST",
    "DEFAULT_RELAY_PORT",
    "DEFAULT_TIMEOUT_MS",
    "HEADER_SIZE",
    "MAX_PAYLOAD_BYTES",
    "PROTOCOL_VERSION",
    "VALID_LOG_TYPES",
    # Models
    "Vector3",
    "Color",
    # Exceptions
    "UnityCLIError",
    "ConnectionError",
    "ProtocolError",
    "InstanceError",
    "TimeoutError",
]


def main() -> None:
    """Entry point for unity-cli command.

    This function is called by pyproject.toml's [project.scripts]:
        unity-cli = "unity_cli:main"
    """
    from unity_cli.cli.app import cli_main

    cli_main()
