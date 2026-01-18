"""Scene API for Unity CLI."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from unity_cli.client import RelayConnection


class SceneAPI:
    """Scene management operations via 'scene' tool."""

    def __init__(self, conn: RelayConnection) -> None:
        self._conn = conn

    def get_active(self) -> dict[str, Any]:
        """Get active scene info.

        Returns:
            Dictionary with active scene information
        """
        return self._conn.send_request("scene", {"action": "active"})

    def get_hierarchy(
        self,
        depth: int = 1,
        page_size: int = 50,
        cursor: int = 0,
    ) -> dict[str, Any]:
        """Get scene hierarchy.

        Args:
            depth: Hierarchy depth to retrieve
            page_size: Number of items per page
            cursor: Pagination cursor

        Returns:
            Dictionary with hierarchy data
        """
        return self._conn.send_request(
            "scene",
            {
                "action": "hierarchy",
                "depth": depth,
                "page_size": page_size,
                "cursor": cursor,
            },
        )

    def load(
        self,
        name: str | None = None,
        path: str | None = None,
        additive: bool = False,
    ) -> dict[str, Any]:
        """Load scene.

        Args:
            name: Scene name to load
            path: Scene path to load (e.g., "Assets/Scenes/Main.unity")
            additive: Load scene additively

        Returns:
            Dictionary with operation result
        """
        params: dict[str, Any] = {"action": "load", "additive": additive}
        if name:
            params["name"] = name
        if path:
            params["path"] = path
        return self._conn.send_request("scene", params)

    def save(self, path: str | None = None) -> dict[str, Any]:
        """Save current scene.

        Args:
            path: Path to save scene to (optional)

        Returns:
            Dictionary with operation result
        """
        params: dict[str, Any] = {"action": "save"}
        if path:
            params["path"] = path
        return self._conn.send_request("scene", params)
