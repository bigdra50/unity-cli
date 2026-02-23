"""UI Tree API for Unity CLI."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from unity_cli.client import RelayConnection

_PANEL_COUNT_RE = re.compile(r"\s+\(\d+\)$")


def _strip_panel_count(name: str) -> str:
    """Remove trailing `` (N)`` suffix from a panel name."""
    return _PANEL_COUNT_RE.sub("", name)


class UITreeAPI:
    """UI Toolkit tree operations."""

    def __init__(self, conn: RelayConnection) -> None:
        self._conn = conn

    def _add_panel_param(self, params: dict[str, Any], panel: str | None) -> None:
        if panel:
            params["panel"] = _strip_panel_count(panel)

    def dump(
        self,
        panel: str | None = None,
        depth: int = -1,
        format: str = "text",
    ) -> dict[str, Any]:
        """Dump UI tree or list panels.

        Args:
            panel: Panel name to dump. If None, lists all panels.
            depth: Maximum tree depth (-1 = unlimited).
            format: Output format ("text" or "json").

        Returns:
            Dictionary containing panel list or tree data.
        """
        params: dict[str, Any] = {"action": "dump", "format": format}
        self._add_panel_param(params, panel)
        if depth != -1:
            params["depth"] = depth
        return self._conn.send_request("uitree", params)

    def query(
        self,
        panel: str,
        type: str | None = None,
        name: str | None = None,
        class_name: str | None = None,
    ) -> dict[str, Any]:
        """Query UI elements by type, name, or class.

        Args:
            panel: Panel name to search in.
            type: Element type filter (e.g., "Button").
            name: Element name filter.
            class_name: USS class filter (e.g., "primary-button").

        Returns:
            Dictionary containing matched elements.
        """
        params: dict[str, Any] = {"action": "query"}
        self._add_panel_param(params, panel)
        if type:
            params["type"] = type
        if name:
            params["name"] = name
        if class_name:
            params["class_name"] = class_name
        return self._conn.send_request("uitree", params)

    def inspect(
        self,
        ref: str | None = None,
        panel: str | None = None,
        name: str | None = None,
        include_style: bool = False,
        include_children: bool = False,
    ) -> dict[str, Any]:
        """Inspect a specific UI element.

        Args:
            ref: Element reference ID (e.g., "ref_3").
            panel: Panel name (used with name).
            name: Element name (used with panel).
            include_style: Include resolvedStyle info.
            include_children: Include children info.

        Returns:
            Dictionary containing element details.
        """
        params: dict[str, Any] = {
            "action": "inspect",
            "include_style": include_style,
            "include_children": include_children,
        }
        if ref:
            params["ref"] = ref
        self._add_panel_param(params, panel)
        if name:
            params["name"] = name
        return self._conn.send_request("uitree", params)

    def click(
        self,
        ref: str | None = None,
        panel: str | None = None,
        name: str | None = None,
        button: int = 0,
        click_count: int = 1,
    ) -> dict[str, Any]:
        """Click a UI element.

        Args:
            ref: Element reference ID (e.g., "ref_3").
            panel: Panel name (used with name).
            name: Element name (used with panel).
            button: Mouse button (0=left, 1=right, 2=middle).
            click_count: Click count (2=double click).

        Returns:
            Dictionary containing click result.
        """
        params: dict[str, Any] = {"action": "click"}
        if ref:
            params["ref"] = ref
        self._add_panel_param(params, panel)
        if name:
            params["name"] = name
        if button != 0:
            params["button"] = button
        if click_count != 1:
            params["click_count"] = click_count
        return self._conn.send_request("uitree", params)

    def scroll(
        self,
        ref: str | None = None,
        panel: str | None = None,
        name: str | None = None,
        x: float | None = None,
        y: float | None = None,
        to_child: str | None = None,
    ) -> dict[str, Any]:
        """Scroll a ScrollView element.

        Args:
            ref: Element reference ID (e.g., "ref_5").
            panel: Panel name (used with name).
            name: Element name (used with panel).
            x: Absolute scroll offset X.
            y: Absolute scroll offset Y.
            to_child: Ref ID of child element to scroll into view.

        Returns:
            Dictionary containing scroll result with scrollOffset.
        """
        params: dict[str, Any] = {"action": "scroll"}
        if ref:
            params["ref"] = ref
        self._add_panel_param(params, panel)
        if name:
            params["name"] = name
        if x is not None:
            params["x"] = x
        if y is not None:
            params["y"] = y
        if to_child:
            params["to_child"] = to_child
        return self._conn.send_request("uitree", params)

    def text(
        self,
        ref: str | None = None,
        panel: str | None = None,
        name: str | None = None,
    ) -> dict[str, Any]:
        """Get text content of a UI element.

        Args:
            ref: Element reference ID (e.g., "ref_7").
            panel: Panel name (used with name).
            name: Element name (used with panel).

        Returns:
            Dictionary containing element text.
        """
        params: dict[str, Any] = {"action": "text"}
        if ref:
            params["ref"] = ref
        self._add_panel_param(params, panel)
        if name:
            params["name"] = name
        return self._conn.send_request("uitree", params)
