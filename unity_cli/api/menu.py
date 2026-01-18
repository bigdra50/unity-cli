"""Menu API for Unity CLI."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from unity_cli.client import RelayConnection


class MenuAPI:
    """Menu operations."""

    def __init__(self, conn: RelayConnection) -> None:
        self._conn = conn

    def execute(self, menu_path: str) -> dict[str, Any]:
        """Execute Unity menu item.

        Args:
            menu_path: Menu item path (e.g., "Assets/Refresh")

        Returns:
            Dictionary with operation result
        """
        return self._conn.send_request("execute_menu_item", {"menu_path": menu_path})
