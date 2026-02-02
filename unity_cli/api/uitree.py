"""UI Tree API for Unity CLI."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from unity_cli.client import RelayConnection


class UITreeAPI:
    """UI Toolkit tree operations."""

    def __init__(self, conn: RelayConnection) -> None:
        self._conn = conn

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
        if panel:
            params["panel"] = panel
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
        params: dict[str, Any] = {"action": "query", "panel": panel}
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
        """
        Retrieve detailed information for a UI element.
        
        Targets an element by `ref`, or by `panel` and `name` when `ref` is not provided. Optionally include resolved style and child data.
        
        Parameters:
            ref (str | None): Element reference ID (e.g., "ref_3").
            panel (str | None): Panel name to locate the element when using `name`.
            name (str | None): Element name within the specified panel.
            include_style (bool): Include resolved style information when True.
            include_children (bool): Include children information when True.
        
        Returns:
            dict[str, Any]: Dictionary containing the element details.
        """
        params: dict[str, Any] = {
            "action": "inspect",
            "include_style": include_style,
            "include_children": include_children,
        }
        if ref:
            params["ref"] = ref
        if panel:
            params["panel"] = panel
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
        """
        Click a UI element.
        
        Parameters:
            ref (str | None): Element reference ID (e.g., "ref_3").
            panel (str | None): Panel name used together with `name` to locate the element.
            name (str | None): Element name used together with `panel` to locate the element.
            button (int): Mouse button to use: 0 = left, 1 = right, 2 = middle.
            click_count (int): Number of clicks (e.g., 2 for double click).
        
        Returns:
            dict[str, Any]: Result dictionary describing the outcome of the click.
        """
        params: dict[str, Any] = {"action": "click"}
        if ref:
            params["ref"] = ref
        if panel:
            params["panel"] = panel
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
        """
        Scroll a ScrollView element to specific coordinates or bring a child element into view.
        
        Parameters:
            ref (str | None): Element reference ID (e.g., "ref_5").
            panel (str | None): Panel name used together with `name`.
            name (str | None): Element name used together with `panel`.
            x (float | None): Absolute horizontal scroll offset.
            y (float | None): Absolute vertical scroll offset.
            to_child (str | None): Ref ID of a child element to scroll into view.
        
        Returns:
            dict[str, Any]: Response containing the scroll result, including `scrollOffset`.
        """
        params: dict[str, Any] = {"action": "scroll"}
        if ref:
            params["ref"] = ref
        if panel:
            params["panel"] = panel
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
        """
        Retrieve the text content of a UI element.
        
        Parameters:
            ref (str | None): Element reference ID (e.g., "ref_7").
            panel (str | None): Panel name to scope the lookup.
            name (str | None): Element name within the panel.
        
        Returns:
            dict[str, Any]: Response dictionary containing the element text.
        """
        params: dict[str, Any] = {"action": "text"}
        if ref:
            params["ref"] = ref
        if panel:
            params["panel"] = panel
        if name:
            params["name"] = name
        return self._conn.send_request("uitree", params)