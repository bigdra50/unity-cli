"""Exit code definitions for Unix-style process status reporting.

Maps UnityCLIError hierarchy to meaningful exit codes so that
shell scripts and CI pipelines can distinguish failure categories.
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from unity_cli.exceptions import UnityCLIError


class ExitCode(enum.IntEnum):
    SUCCESS = 0
    USAGE_ERROR = 1
    TRANSIENT_ERROR = 2
    CONNECTION_ERROR = 3
    OPERATION_ERROR = 4
    TEST_FAILURE = 5


_TRANSIENT_CODES = frozenset({"INSTANCE_RELOADING", "INSTANCE_BUSY"})


def exit_code_for(exc: UnityCLIError) -> ExitCode:
    """Map a UnityCLIError to the appropriate exit code."""
    from unity_cli.exceptions import ConnectionError, InstanceError, TimeoutError

    if isinstance(exc, ConnectionError):
        return ExitCode.CONNECTION_ERROR
    if isinstance(exc, TimeoutError):
        return ExitCode.TRANSIENT_ERROR
    if isinstance(exc, InstanceError):
        if exc.code in _TRANSIENT_CODES:
            return ExitCode.TRANSIENT_ERROR
        return ExitCode.OPERATION_ERROR
    return ExitCode.OPERATION_ERROR
