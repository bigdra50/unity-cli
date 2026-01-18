"""Editor API for Unity CLI."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from unity_cli.client import RelayConnection


class EditorAPI:
    """Editor control operations."""

    def __init__(self, conn: RelayConnection) -> None:
        self._conn = conn

    def play(self) -> dict[str, Any]:
        """Enter play mode.

        Returns:
            Dictionary with operation result
        """
        return self._conn.send_request("playmode", {"action": "enter"})

    def pause(self) -> dict[str, Any]:
        """Pause/unpause game.

        Returns:
            Dictionary with operation result
        """
        return self._conn.send_request("playmode", {"action": "pause"})

    def unpause(self) -> dict[str, Any]:
        """Unpause game.

        Returns:
            Dictionary with operation result
        """
        return self._conn.send_request("playmode", {"action": "unpause"})

    def stop(self) -> dict[str, Any]:
        """Exit play mode.

        Returns:
            Dictionary with operation result
        """
        return self._conn.send_request("playmode", {"action": "exit"})

    def step(self) -> dict[str, Any]:
        """Step one frame.

        Returns:
            Dictionary with operation result
        """
        return self._conn.send_request("playmode", {"action": "step"})

    def get_state(self) -> dict[str, Any]:
        """Get editor state.

        Returns:
            Dictionary with editor state information
        """
        return self._conn.send_request("playmode", {"action": "state"})

    def get_tags(self) -> dict[str, Any]:
        """Get all tags.

        Returns:
            Dictionary with all available tags
        """
        return self._conn.send_request("get_tags", {})

    def get_layers(self) -> dict[str, Any]:
        """Get all layers.

        Returns:
            Dictionary with all available layers
        """
        return self._conn.send_request("get_layers", {})

    def refresh(self) -> dict[str, Any]:
        """Refresh asset database (triggers recompilation).

        Returns:
            Dictionary with operation result
        """
        return self._conn.send_request("refresh", {})
