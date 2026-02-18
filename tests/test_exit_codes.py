"""Tests for exit code mapping."""

from __future__ import annotations

import pytest

from unity_cli.cli.exit_codes import ExitCode, exit_code_for
from unity_cli.exceptions import (
    ConnectionError,
    HubError,
    InstanceError,
    ProjectError,
    ProtocolError,
    TimeoutError,
    UnityCLIError,
)


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (ConnectionError("refused", "CONNECTION_FAILED"), ExitCode.CONNECTION_ERROR),
        (TimeoutError("timed out", "TIMEOUT"), ExitCode.TRANSIENT_ERROR),
        (TimeoutError("retry", "RETRY_TIMEOUT"), ExitCode.TRANSIENT_ERROR),
        (InstanceError("reloading", "INSTANCE_RELOADING"), ExitCode.TRANSIENT_ERROR),
        (InstanceError("busy", "INSTANCE_BUSY"), ExitCode.TRANSIENT_ERROR),
        (InstanceError("not found", "INSTANCE_NOT_FOUND"), ExitCode.INSTANCE_ERROR),
        (InstanceError("ambiguous", "AMBIGUOUS_INSTANCE"), ExitCode.INSTANCE_ERROR),
        (ProtocolError("bad frame", "PROTOCOL_ERROR"), ExitCode.INSTANCE_ERROR),
        (HubError("hub error"), ExitCode.INSTANCE_ERROR),
        (ProjectError("project error"), ExitCode.INSTANCE_ERROR),
        (UnityCLIError("unknown", "UNKNOWN"), ExitCode.INSTANCE_ERROR),
    ],
    ids=[
        "ConnectionError",
        "TimeoutError-TIMEOUT",
        "TimeoutError-RETRY_TIMEOUT",
        "InstanceError-RELOADING",
        "InstanceError-BUSY",
        "InstanceError-NOT_FOUND",
        "InstanceError-AMBIGUOUS",
        "ProtocolError",
        "HubError",
        "ProjectError",
        "UnityCLIError-generic",
    ],
)
def test_exit_code_for(exc: UnityCLIError, expected: ExitCode) -> None:
    assert exit_code_for(exc) == expected


def test_exit_codes_are_ints() -> None:
    assert ExitCode.SUCCESS == 0
    assert ExitCode.USAGE_ERROR == 1
    assert ExitCode.TRANSIENT_ERROR == 2
    assert ExitCode.CONNECTION_ERROR == 3
    assert ExitCode.INSTANCE_ERROR == 4
