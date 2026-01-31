"""Profiler API for Unity CLI."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from unity_cli.client import RelayConnection


class ProfilerAPI:
    """Profiler operations via Relay Server."""

    def __init__(self, conn: RelayConnection) -> None:
        self._conn = conn

    def status(self) -> dict[str, Any]:
        """Get profiler status."""
        return self._conn.send_request("profiler", {"action": "status"})

    def start(self) -> dict[str, Any]:
        """Start profiling."""
        return self._conn.send_request("profiler", {"action": "start"})

    def stop(self) -> dict[str, Any]:
        """Stop profiling."""
        return self._conn.send_request("profiler", {"action": "stop"})

    def snapshot(self) -> dict[str, Any]:
        """Get current frame profiler data."""
        return self._conn.send_request("profiler", {"action": "snapshot"})

    def frames(self, count: int = 10) -> dict[str, Any]:
        """Get recent N frames summary.

        Args:
            count: Number of frames to retrieve (default: 10)
        """
        return self._conn.send_request(
            "profiler",
            {"action": "frames", "count": count},
        )
