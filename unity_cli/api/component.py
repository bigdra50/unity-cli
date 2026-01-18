"""Component API for Unity CLI."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from unity_cli.client import RelayConnection


class ComponentAPI:
    """Component operations via 'component' tool."""

    def __init__(self, conn: RelayConnection) -> None:
        self._conn = conn

    def list(
        self,
        target: str | None = None,
        target_id: int | None = None,
    ) -> dict[str, Any]:
        """List components on a GameObject.

        Args:
            target: Target GameObject name
            target_id: Target GameObject instance ID

        Returns:
            Dictionary with component list
        """
        params: dict[str, Any] = {"action": "list"}
        if target:
            params["target"] = target
        if target_id is not None:
            params["targetId"] = target_id
        return self._conn.send_request("component", params)

    def inspect(
        self,
        component_type: str,
        target: str | None = None,
        target_id: int | None = None,
    ) -> dict[str, Any]:
        """Inspect component properties.

        Args:
            component_type: Component type name to inspect
            target: Target GameObject name
            target_id: Target GameObject instance ID

        Returns:
            Dictionary with component properties
        """
        params: dict[str, Any] = {"action": "inspect", "type": component_type}
        if target:
            params["target"] = target
        if target_id is not None:
            params["targetId"] = target_id
        return self._conn.send_request("component", params)
