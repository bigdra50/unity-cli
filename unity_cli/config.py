"""
Unity CLI Configuration Module
==============================

Pydantic v2 based configuration for Unity CLI Client.
Supports TOML file loading and validation.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field

# =============================================================================
# Protocol Constants
# =============================================================================

PROTOCOL_VERSION = "1.0"
DEFAULT_RELAY_HOST = "127.0.0.1"
DEFAULT_RELAY_PORT = 6500
HEADER_SIZE = 4
MAX_PAYLOAD_BYTES = 16 * 1024 * 1024  # 16 MiB
DEFAULT_TIMEOUT_MS = 30000
CONFIG_FILE_NAME = ".unity-cli.toml"


# =============================================================================
# Configuration Model
# =============================================================================


class UnityCLIConfig(BaseModel):
    """Configuration for Unity CLI Client.

    Attributes:
        relay_host: Relay server hostname or IP address.
        relay_port: Relay server port (1-65535).
        timeout: TCP socket timeout in seconds (for connect/read operations).
        timeout_ms: Unity command timeout in milliseconds (for command execution).
        instance: Target Unity instance path (optional).
        retry_initial_ms: Initial retry backoff interval in milliseconds.
        retry_max_ms: Maximum retry backoff interval in milliseconds.
        retry_max_time_ms: Maximum total retry time in milliseconds.

    Note:
        `timeout` and `timeout_ms` serve different purposes:
        - `timeout`: Low-level socket operation timeout (seconds)
        - `timeout_ms`: High-level Unity command execution timeout (milliseconds)
    """

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=False,
        extra="ignore",
    )

    relay_host: str = DEFAULT_RELAY_HOST
    relay_port: Annotated[int, Field(gt=0, le=65535)] = DEFAULT_RELAY_PORT
    timeout: Annotated[float, Field(gt=0)] = 15.0
    timeout_ms: Annotated[int, Field(gt=0)] = DEFAULT_TIMEOUT_MS
    instance: str | None = None
    retry_initial_ms: Annotated[int, Field(gt=0)] = 500
    retry_max_ms: Annotated[int, Field(gt=0)] = 8000
    retry_max_time_ms: Annotated[int, Field(gt=0)] = 45000

    @classmethod
    def load(cls, config_path: Path | None = None) -> Self:
        """Load configuration from TOML file.

        Args:
            config_path: Path to TOML config file. If None, searches for
                         .unity-cli.toml in current directory or Unity project root.

        Returns:
            UnityCLIConfig instance with loaded or default values.
        """
        toml_path = config_path if config_path and config_path.exists() else cls._find_config_file()

        if toml_path:
            try:
                with open(toml_path, "rb") as f:
                    data = tomllib.load(f)
                return cls.model_validate(data)
            except (tomllib.TOMLDecodeError, OSError):
                pass

        return cls()

    @classmethod
    def _find_config_file(cls) -> Path | None:
        """Find config file in current directory or Unity project root.

        Returns:
            Path to config file if found, None otherwise.
        """
        cwd = Path.cwd()

        # Check current directory first
        config_in_cwd = cwd / CONFIG_FILE_NAME
        if config_in_cwd.exists():
            return config_in_cwd

        # Search for Unity project root
        for parent in [cwd, *list(cwd.parents)]:
            if (parent / "Assets").is_dir() and (parent / "ProjectSettings").is_dir():
                config_in_project = parent / CONFIG_FILE_NAME
                if config_in_project.exists():
                    return config_in_project
                break

        return None

    def to_toml(self) -> str:
        """Generate TOML string from config.

        Returns:
            TOML formatted configuration string.
        """
        instance_str = f'"{self.instance}"' if self.instance else "# not set"

        return f'''# Unity CLI Configuration

relay_host = "{self.relay_host}"
relay_port = {self.relay_port}
timeout = {self.timeout}
timeout_ms = {self.timeout_ms}
instance = {instance_str}

# Retry settings (exponential backoff)
retry_initial_ms = {self.retry_initial_ms}
retry_max_ms = {self.retry_max_ms}
retry_max_time_ms = {self.retry_max_time_ms}
'''
