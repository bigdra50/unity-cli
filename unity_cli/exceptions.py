"""
Unity CLI Exception Classes
============================

Exception hierarchy for Unity CLI operations.

Hierarchy:
    UnityCLIError (base)
    ├── ConnectionError - Relay server connection failures
    ├── ProtocolError - Protocol/message framing errors
    ├── InstanceError - Unity instance-related errors
    └── TimeoutError - Command/response timeouts
"""

from __future__ import annotations


class UnityCLIError(Exception):
    """Base exception for Unity CLI operations.

    Attributes:
        code: Optional error code for programmatic handling
    """

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code

    def __str__(self) -> str:
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message


class ConnectionError(UnityCLIError):
    """Relay server connection failure.

    Raised when:
    - Cannot establish TCP connection to relay server
    - Connection refused or timed out
    """

    pass


class ProtocolError(UnityCLIError):
    """Protocol-level error.

    Raised when:
    - Invalid message framing (header size mismatch)
    - Payload exceeds maximum size (16 MiB)
    - Malformed JSON in response
    - Unexpected message type
    """

    pass


class InstanceError(UnityCLIError):
    """Unity instance-related error.

    Raised when:
    - INSTANCE_NOT_FOUND: No Unity instance connected
    - INSTANCE_RELOADING: Unity is in domain reload
    - INSTANCE_BUSY: Unity is processing another command
    """

    pass


class TimeoutError(UnityCLIError):
    """Command or response timeout.

    Raised when:
    - Response not received within timeout period
    - Max retry time exceeded for retryable errors
    """

    pass
