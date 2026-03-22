"""Dynamic API for invoking arbitrary Unity static methods."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from unity_cli.api.schema_cache import SchemaCache
from unity_cli.exceptions import UnityCLIError

if TYPE_CHECKING:
    from unity_cli.client import RelayConnection


class DynamicAPI:
    """Dynamic Unity API invocation and schema introspection."""

    def __init__(self, conn: RelayConnection) -> None:
        self._conn = conn
        self._cache = SchemaCache()

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
        offline: bool = False,
        no_cache: bool = False,
        version: str | None = None,
    ) -> dict[str, Any]:
        """List available Unity static API methods.

        Args:
            namespace: Filter by namespace prefixes.
            type_name: Filter by type name.
            method_name: Filter by method name.
            limit: Maximum results per page.
            offset: Pagination offset.
            offline: Use cached schema only (no Relay).
            no_cache: Skip cache, fetch from Relay.
            version: Unity version override (for offline use).

        Returns:
            Dictionary with methods, total, and hasMore.
        """
        # Try cache first (unless no_cache)
        if not no_cache:
            cache_version = version or self._get_unity_version_safe()
            if cache_version:
                cached = self._cache.get(cache_version)
                if cached:
                    return self._filter_schema(cached, namespace, type_name, method_name, limit, offset)

        if offline:
            raise UnityCLIError(
                "No cached schema available. Run 'u api schema' with Relay connected first, or specify --version.",
                "CACHE_MISS",
            )

        # Fetch full schema from Relay and cache it
        full = self._conn.send_request("api-schema", {"cache_all": True})
        relay_version = version or self._get_unity_version_safe()
        if relay_version:
            full["version"] = relay_version
            self._cache.put(relay_version, full)

        return self._filter_schema(full, namespace, type_name, method_name, limit, offset)

    def _get_unity_version_safe(self) -> str | None:
        """Get Unity version from connected instance, or None."""
        try:
            instances = self._conn.list_instances()
            for inst in instances:
                if inst.get("unity_version"):
                    version: str = inst["unity_version"]
                    return version
        except Exception:
            pass
        return None

    def _filter_schema(
        self,
        schema: dict[str, Any],
        namespace: list[str] | None,
        type_name: str | None,
        method_name: str | None,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        """Filter and paginate a full schema."""
        methods: list[dict[str, Any]] = schema.get("methods", [])

        if namespace:
            methods = _filter_by_namespace(methods, namespace)
        if type_name:
            methods = _filter_by_type(methods, type_name)
        if method_name:
            methods = _filter_by_method(methods, method_name)

        total = len(methods)
        page = methods[offset : offset + limit]

        return {
            "methods": page,
            "total": total,
            "hasMore": offset + limit < total,
        }


def _filter_by_namespace(methods: list[dict[str, Any]], namespaces: list[str]) -> list[dict[str, Any]]:
    return [m for m in methods if any(m.get("type", "").startswith(ns) for ns in namespaces)]


def _filter_by_type(methods: list[dict[str, Any]], type_name: str) -> list[dict[str, Any]]:
    tl = type_name.lower()
    return [m for m in methods if m.get("type", "").lower().endswith(f".{tl}") or m.get("type", "").lower() == tl]


def _filter_by_method(methods: list[dict[str, Any]], method_name: str) -> list[dict[str, Any]]:
    ml = method_name.lower()
    return [m for m in methods if m.get("method", "").lower() == ml]
