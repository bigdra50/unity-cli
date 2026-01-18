"""Material API for Unity CLI."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from unity_cli.client import RelayConnection


class MaterialAPI:
    """Material management operations."""

    def __init__(self, conn: RelayConnection) -> None:
        self._conn = conn

    def create(
        self,
        material_path: str,
        shader: str = "Standard",
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create material.

        Args:
            material_path: Path for the new material
            shader: Shader name (default: "Standard")
            properties: Optional material properties

        Returns:
            Dictionary with created material info
        """
        params: dict[str, Any] = {
            "action": "create",
            "materialPath": material_path,
            "shader": shader,
        }
        if properties:
            params["properties"] = properties

        return self._conn.send_request("manage_material", params)

    def set_color(
        self,
        material_path: str,
        color: list[float],
        property: str = "_BaseColor",
    ) -> dict[str, Any]:
        """Set material color.

        Args:
            material_path: Path to the material
            color: Color as [r, g, b, a] list
            property: Shader property name (default: "_BaseColor")

        Returns:
            Dictionary with operation result
        """
        return self._conn.send_request(
            "manage_material",
            {
                "action": "set_color",
                "materialPath": material_path,
                "color": color,
                "property": property,
            },
        )

    def get_info(self, material_path: str) -> dict[str, Any]:
        """Get material info.

        Args:
            material_path: Path to the material

        Returns:
            Dictionary with material information
        """
        return self._conn.send_request(
            "manage_material",
            {"action": "get_info", "materialPath": material_path},
        )
