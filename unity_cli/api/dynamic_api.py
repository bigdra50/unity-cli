"""Dynamic API for invoking arbitrary Unity static methods."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from unity_cli.client import RelayConnection


class DynamicAPI:
    """Dynamic Unity API invocation and schema introspection."""

    def __init__(self, conn: RelayConnection) -> None:
        self._conn = conn

    def invoke(
        self,
        type_name: str,
        method_name: str,
        params: list[Any] | None = None,
    ) -> dict[str, Any]:
        """Invoke a Unity public static method by reflection.

        Args:
            type_name: Fully qualified type name (e.g., "UnityEditor.AssetDatabase").
            method_name: Static method name (e.g., "Refresh").
            params: Ordered arguments as a JSON-serializable list.

        Returns:
            Dictionary with type, method, returnType, and result.
        """
        return self._conn.send_request(
            "api-invoke",
            {"type": type_name, "method": method_name, "params": params or []},
        )

    def schema(
        self,
        namespace: list[str] | None = None,
        type_name: str | None = None,
        method_name: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """List available Unity static API methods.

        Args:
            namespace: Filter by namespace prefixes.
            type_name: Filter by type name.
            method_name: Filter by method name.
            limit: Maximum results per page.
            offset: Pagination offset.

        Returns:
            Dictionary with methods, total, and hasMore.
        """
        p: dict[str, Any] = {"limit": limit, "offset": offset}
        if namespace:
            p["namespace"] = namespace
        if type_name:
            p["type"] = type_name
        if method_name:
            p["method"] = method_name
        return self._conn.send_request("api-schema", p)
