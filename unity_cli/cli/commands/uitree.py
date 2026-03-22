"""UI Toolkit tree commands: dump, query, inspect, click, scroll, text, monkey, snapshot."""

from __future__ import annotations

from typing import Annotated, Any

import typer
from rich.markup import escape

from unity_cli.cli.context import CLIContext
from unity_cli.cli.helpers import _exit_usage, _handle_error, _should_json, handle_cli_errors
from unity_cli.cli.output import (
    is_no_color,
    print_json,
    print_key_value,
    print_line,
    print_plain_table,
    print_success,
    sanitize_tsv,
)
from unity_cli.exceptions import UnityCLIError

uitree_app = typer.Typer(help="UI Toolkit tree commands")
snapshot_app = typer.Typer(help="UI tree snapshot commands")
uitree_app.add_typer(snapshot_app, name="snapshot")


@uitree_app.command("dump")
def uitree_dump(
    ctx: typer.Context,
    panel: Annotated[
        str | None,
        typer.Option("--panel", "-p", help="Panel name (omit to list panels)"),
    ] = None,
    depth: Annotated[
        int,
        typer.Option("--depth", "-d", help="Max tree depth (-1 = unlimited)"),
    ] = -1,
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Dump UI tree or list panels.

    Examples:
        u uitree dump                              # List panels
        u uitree dump -p "GameView"                # Dump tree as text
        u uitree dump -p "GameView" --json         # Dump tree as JSON
        u uitree dump -p "GameView" -d 3           # Limit depth
    """
    context: CLIContext = ctx.obj
    try:
        server_format = "json" if json_flag or context.output.is_json else "text"
        result = context.client.uitree.dump(
            panel=panel,
            depth=depth,
            format=server_format,
        )

        if _should_json(context, json_flag):
            print_json(result, None)
        elif panel:
            # Tree output for a specific panel
            panel_name = result.get("panel", panel)
            element_count = result.get("elementCount", 0)
            print_line(f"Panel: {panel_name} ({element_count} elements)\n")

            tree_text = result.get("tree", "")
            if tree_text:
                print_line(tree_text)
        else:
            # Panel list
            panels = result.get("panels", [])
            if not panels:
                print_line("[dim]No panels found[/dim]")
                return

            for p in panels:
                print_line(_format_panel_list_entry(p))

    except UnityCLIError as e:
        _handle_error(e)


@uitree_app.command("query")
def uitree_query(
    ctx: typer.Context,
    panel: Annotated[
        str,
        typer.Option("--panel", "-p", help="Panel name"),
    ],
    type_filter: Annotated[
        str | None,
        typer.Option("--type", "-t", help="Element type filter"),
    ] = None,
    name_filter: Annotated[
        str | None,
        typer.Option("--name", "-n", help="Element name filter"),
    ] = None,
    class_filter: Annotated[
        str | None,
        typer.Option("--class", "-c", help="USS class filter"),
    ] = None,
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Query UI elements by type, name, or class.

    Filters are combined as AND conditions.

    Examples:
        u uitree query -p "GameView" -t Button
        u uitree query -p "GameView" -n "StartBtn"
        u uitree query -p "GameView" -c "primary-button"
        u uitree query -p "GameView" -t Button -c "primary-button"
    """
    context: CLIContext = ctx.obj
    try:
        result = context.client.uitree.query(
            panel=panel,
            type=type_filter,
            name=name_filter,
            class_name=class_filter,
        )

        if _should_json(context, json_flag):
            print_json(result, None)
        elif is_no_color():
            matches = result.get("matches", [])
            for elem in matches:
                _print_query_match_plain(elem)
        else:
            matches = result.get("matches", [])
            count = result.get("count", len(matches))
            print_line(f'Found {count} elements in "{panel}":\n')

            if not matches:
                print_line("[dim]No matching elements[/dim]")
                return

            for elem in matches:
                for line in _format_query_match(elem):
                    print_line(line)

    except UnityCLIError as e:
        _handle_error(e)


@uitree_app.command("inspect")
def uitree_inspect(
    ctx: typer.Context,
    ref: Annotated[
        str | None,
        typer.Argument(help="Element reference ID (e.g., ref_3)"),
    ] = None,
    panel: Annotated[
        str | None,
        typer.Option("--panel", "-p", help="Panel name"),
    ] = None,
    name: Annotated[
        str | None,
        typer.Option("--name", "-n", help="Element name"),
    ] = None,
    style: Annotated[
        bool,
        typer.Option("--style", "-s", help="Include resolvedStyle"),
    ] = False,
    children: Annotated[
        bool,
        typer.Option("--children", help="Include children info"),
    ] = False,
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Inspect a specific UI element.

    Specify element by ref ID or by panel + name.

    Examples:
        u uitree inspect ref_3
        u uitree inspect -p "GameView" -n "StartBtn"
        u uitree inspect ref_3 --style
        u uitree inspect ref_3 --children
    """
    context: CLIContext = ctx.obj

    if not ref and not (panel and name):
        _exit_usage("ref argument or --panel + --name required", "u uitree inspect")

    try:
        result = context.client.uitree.inspect(
            ref=ref,
            panel=panel,
            name=name,
            include_style=style,
            include_children=children,
        )

        if _should_json(context, json_flag):
            print_json(result, None)
        elif is_no_color():
            _print_inspect_element_plain(result)
        else:
            for line in _format_inspect_element(result):
                print_line(line)

    except UnityCLIError as e:
        _handle_error(e)


# ---------------------------------------------------------------------------
# uitree format helpers (pure functions returning list[str])
# ---------------------------------------------------------------------------


def _format_panel_list_entry(panel: dict[str, Any]) -> str:
    """Format a single panel entry for pipe-friendly output."""
    name = escape(panel.get("name", ""))
    count = panel.get("elementCount", 0)
    return f"{name} ({count})"


def _format_rect_value(rect: dict[str, Any]) -> str:
    """Format rect dict as (x, y, wxh) string."""
    return f"({rect.get('x', 0)}, {rect.get('y', 0)}, {rect.get('width', 0)}x{rect.get('height', 0)})"


def _format_rect(rect: dict[str, Any], label: str) -> str:
    return f"  {label}: {_format_rect_value(rect)}"


def _format_element_header(elem: dict[str, Any]) -> list[str]:
    """Format ref/type/name header line and classes."""
    lines: list[str] = []
    header_parts = [p for p in [elem.get("ref", ""), elem.get("type", "VisualElement")] if p]
    elem_name = elem.get("name", "")
    if elem_name:
        header_parts.append(f'"{elem_name}"')
    lines.append(" ".join(header_parts))

    classes = elem.get("classes")
    if isinstance(classes, list) and classes:
        lines.append(f"  classes: {' '.join('.' + str(c) for c in classes)}")
    return lines


def _format_enabled(elem: dict[str, Any]) -> str | None:
    """Format enabled status line, or None if absent."""
    if "enabledSelf" not in elem:
        return None
    suffix = f" (hierarchy: {elem['enabledInHierarchy']})" if "enabledInHierarchy" in elem else ""
    return f"  enabled: {elem['enabledSelf']}{suffix}"


def _format_element_detail(elem: dict[str, Any]) -> list[str]:
    """Format visible, enabled, focusable, layout, worldBound, childCount, path."""
    lines: list[str] = []
    for key in ("visible", "focusable"):
        if key in elem:
            lines.append(f"  {key}: {elem[key]}")

    enabled = _format_enabled(elem)
    if enabled:
        lines.append(enabled)

    for key in ("layout", "worldBound"):
        rect = elem.get(key)
        if isinstance(rect, dict) and rect:
            lines.append(_format_rect(rect, key))

    for key in ("childCount", "path"):
        val = elem.get(key)
        if val is not None and val != "":
            lines.append(f"  {key}: {val}")
    return lines


def _format_element_style(style_data: Any) -> list[str]:
    """Format resolvedStyle section."""
    if not style_data or not isinstance(style_data, dict):
        return []
    lines: list[str] = ["  resolvedStyle:"]
    for k, v in style_data.items():
        lines.append(f"    {k}: {v}")
    return lines


def _format_element_children(children_data: Any) -> list[str]:
    """Format children section."""
    if not children_data or not isinstance(children_data, list):
        return []
    lines: list[str] = ["  children:"]
    for child in children_data:
        if not isinstance(child, dict):
            continue
        parts = ["  " + child.get("ref", ""), child.get("type", "VisualElement")]
        child_name = child.get("name", "")
        if child_name:
            parts.append(f'"{child_name}"')
        lines.append(" ".join(parts))
    return lines


def _format_inspect_element(elem: dict[str, Any]) -> list[str]:
    """Format a full inspect element (header + detail + style + children)."""
    lines: list[str] = []
    lines.extend(_format_element_header(elem))
    lines.extend(_format_element_detail(elem))
    style_lines = _format_element_style(elem.get("resolvedStyle"))
    if style_lines:
        lines.append("")
        lines.extend(style_lines)
    children_lines = _format_element_children(elem.get("children"))
    if children_lines:
        lines.append("")
        lines.extend(children_lines)
    return lines


def _print_query_match_plain(elem: dict[str, Any]) -> None:
    """Print a single query match as tab-separated line for pipe-friendly output."""
    ref = elem.get("ref", "")
    type_name = elem.get("type", "VisualElement")
    elem_name = elem.get("name", "")
    path = elem.get("path", "")
    layout = elem.get("layout")
    layout_str = ""
    if isinstance(layout, dict) and layout:
        layout_str = f"{layout.get('x', 0)},{layout.get('y', 0)},{layout.get('width', 0)}x{layout.get('height', 0)}"
    row = [ref, type_name, elem_name, path, layout_str]
    print_plain_table(["Ref", "Type", "Name", "Path", "Layout"], [row], header=False)


_INSPECT_NONEMPTY_KEYS = ("ref", "type", "name", "childCount", "path")
_INSPECT_PRESENT_KEYS = ("visible", "focusable", "enabledSelf", "enabledInHierarchy")
_INSPECT_RECT_KEYS = ("layout", "worldBound")


def _extract_nonempty(elem: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    """Extract non-empty values for given keys."""
    return {k: elem[k] for k in keys if elem.get(k) is not None and elem.get(k) != ""}


def _extract_present(elem: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    """Extract values that are present (key exists) regardless of value."""
    return {k: elem[k] for k in keys if k in elem}


def _extract_rects(elem: dict[str, Any], keys: tuple[str, ...]) -> dict[str, str]:
    """Extract rect keys and format them."""
    result: dict[str, str] = {}
    for k in keys:
        rect = elem.get(k)
        if isinstance(rect, dict) and rect:
            result[k] = _format_rect_value(rect)
    return result


def _build_inspect_kv(elem: dict[str, Any]) -> dict[str, Any]:
    """Build key-value dict from inspect element for plain output."""
    kv: dict[str, Any] = _extract_nonempty(elem, _INSPECT_NONEMPTY_KEYS)
    classes = elem.get("classes")
    if isinstance(classes, list) and classes:
        kv["classes"] = " ".join(f".{c}" for c in classes)
    kv.update(_extract_present(elem, _INSPECT_PRESENT_KEYS))
    kv.update(_extract_rects(elem, _INSPECT_RECT_KEYS))
    return kv


def _print_inspect_element_plain(elem: dict[str, Any]) -> None:
    """Print inspect element as tab-separated K-V for pipe-friendly output."""
    print_key_value(_build_inspect_kv(elem))

    # style: dot notation
    style_data = elem.get("resolvedStyle")
    if style_data and isinstance(style_data, dict):
        style_rows = [[f"style.{sanitize_tsv(str(k))}", str(v)] for k, v in style_data.items()]
        print_plain_table(["Key", "Value"], style_rows, header=False)

    # children: one line per child
    children_data = elem.get("children")
    if children_data and isinstance(children_data, list):
        for child in children_data:
            if not isinstance(child, dict):
                continue
            child_row = ["child", child.get("ref", ""), child.get("type", "VisualElement"), child.get("name", "")]
            print_plain_table(["Prefix", "Ref", "Type", "Name"], [child_row], header=False)


def _format_query_match(elem: dict[str, Any]) -> list[str]:
    """Format a single query match element."""
    lines: list[str] = []
    ref = elem.get("ref", "")
    type_name = elem.get("type", "VisualElement")
    elem_name = elem.get("name", "")
    classes = elem.get("classes")

    parts = [f"  {ref}", type_name]
    if elem_name:
        parts.append(f'"{elem_name}"')
    if isinstance(classes, list):
        for cls in classes:
            parts.append(f".{cls}")
    lines.append(" ".join(parts))

    path = elem.get("path", "")
    if path:
        lines.append(f"    [dim]path: {path}[/dim]")

    layout = elem.get("layout")
    if isinstance(layout, dict) and layout:
        lines.append(f"    [dim]layout: {_format_rect_value(layout)}[/dim]")

    lines.append("")
    return lines


@uitree_app.command("click")
def uitree_click(
    ctx: typer.Context,
    ref: Annotated[
        str | None,
        typer.Argument(help="Element reference ID (e.g., ref_3)"),
    ] = None,
    panel: Annotated[
        str | None,
        typer.Option("--panel", "-p", help="Panel name"),
    ] = None,
    name: Annotated[
        str | None,
        typer.Option("--name", "-n", help="Element name"),
    ] = None,
    button: Annotated[
        int,
        typer.Option("--button", "-b", help="Mouse button (0=left, 1=right, 2=middle)"),
    ] = 0,
    count: Annotated[
        int,
        typer.Option("--count", "-c", help="Click count (2=double click)"),
    ] = 1,
) -> None:
    """Click a UI element.

    Specify element by ref ID or by panel + name.

    Examples:
        u uitree click ref_3                          # Left click
        u uitree click ref_3 --button 1               # Right click
        u uitree click ref_3 --count 2                # Double click
        u uitree click -p "GameView" -n "StartBtn"    # By panel + name
    """
    context: CLIContext = ctx.obj

    if not ref and not (panel and name):
        _exit_usage("ref argument or --panel + --name required", "u uitree click")

    if button not in (0, 1, 2):
        _exit_usage("--button must be 0 (left), 1 (right), or 2 (middle)", "u uitree click")

    if count < 1:
        _exit_usage("--count must be a positive integer (>= 1)", "u uitree click")

    try:
        result = context.client.uitree.click(
            ref=ref,
            panel=panel,
            name=name,
            button=button,
            click_count=count,
        )

        elem_ref = result.get("ref", "")
        elem_type = escape(result.get("type", ""))
        msg = escape(result.get("message", ""))
        print_line(f"{elem_ref} {elem_type}: {msg}")

    except UnityCLIError as e:
        _handle_error(e)


@uitree_app.command("scroll")
def uitree_scroll(
    ctx: typer.Context,
    ref: Annotated[
        str | None,
        typer.Argument(help="Element reference ID (e.g., ref_5)"),
    ] = None,
    panel: Annotated[
        str | None,
        typer.Option("--panel", "-p", help="Panel name"),
    ] = None,
    name: Annotated[
        str | None,
        typer.Option("--name", "-n", help="Element name"),
    ] = None,
    x: Annotated[
        float | None,
        typer.Option("--x", help="Scroll offset X (absolute)"),
    ] = None,
    y: Annotated[
        float | None,
        typer.Option("--y", help="Scroll offset Y (absolute)"),
    ] = None,
    to: Annotated[
        str | None,
        typer.Option("--to", help="Ref ID of child element to scroll into view"),
    ] = None,
) -> None:
    """Scroll a ScrollView element.

    Two modes:
      Offset mode: --x and/or --y to set absolute scroll position.
      ScrollTo mode: --to <ref_id> to scroll a child element into view.

    Examples:
        u uitree scroll ref_5 --y 0                   # Scroll to top
        u uitree scroll ref_5 --y 500                  # Scroll to y=500
        u uitree scroll ref_5 --to ref_12              # Scroll child into view
    """
    context: CLIContext = ctx.obj

    if not ref and not (panel and name):
        _exit_usage("ref argument or --panel + --name required", "u uitree scroll")

    if to is None and x is None and y is None:
        _exit_usage("--x/--y or --to parameter required", "u uitree scroll")

    try:
        result = context.client.uitree.scroll(
            ref=ref,
            panel=panel,
            name=name,
            x=x,
            y=y,
            to_child=to,
        )

        elem_ref = escape(result.get("ref", ""))
        offset = result.get("scrollOffset", {})
        ox = offset.get("x", 0)
        oy = offset.get("y", 0)
        print_line(f"{elem_ref} ScrollView: scrollOffset=({ox}, {oy})")

    except UnityCLIError as e:
        _handle_error(e)


@uitree_app.command("text")
def uitree_text(
    ctx: typer.Context,
    ref: Annotated[
        str | None,
        typer.Argument(help="Element reference ID (e.g., ref_7)"),
    ] = None,
    panel: Annotated[
        str | None,
        typer.Option("--panel", "-p", help="Panel name"),
    ] = None,
    name: Annotated[
        str | None,
        typer.Option("--name", "-n", help="Element name"),
    ] = None,
) -> None:
    """Get text content of a UI element.

    Specify element by ref ID or by panel + name.

    Examples:
        u uitree text ref_7                           # Get text by ref
        u uitree text -p "GameView" -n "TitleLabel"   # By panel + name
    """
    context: CLIContext = ctx.obj

    if not ref and not (panel and name):
        _exit_usage("ref argument or --panel + --name required", "u uitree text")

    try:
        result = context.client.uitree.text(
            ref=ref,
            panel=panel,
            name=name,
        )

        elem_ref = result.get("ref", "")
        elem_type = escape(result.get("type", ""))
        text = escape(result.get("text", ""))
        print_line(f"{elem_ref} {elem_type}: {text}")

    except UnityCLIError as e:
        _handle_error(e)


# =============================================================================
# monkey
# =============================================================================


@uitree_app.command("monkey")
@handle_cli_errors
def uitree_monkey(
    ctx: typer.Context,
    panel: Annotated[
        str,
        typer.Option("--panel", "-p", help="Target panel name"),
    ],
    duration: Annotated[
        float | None,
        typer.Option("--duration", help="Max duration in seconds"),
    ] = None,
    count: Annotated[
        int | None,
        typer.Option("--count", "-n", help="Max number of actions"),
    ] = None,
    seed: Annotated[
        int | None,
        typer.Option("--seed", help="Random seed for reproducibility"),
    ] = None,
    type_filter: Annotated[
        str | None,
        typer.Option("--type", "-t", help="Filter elements by type"),
    ] = None,
    class_filter: Annotated[
        str | None,
        typer.Option("--class", "-c", help="Filter elements by USS class"),
    ] = None,
    stop_on_error: Annotated[
        bool,
        typer.Option("--stop-on-error", help="Stop on first console error"),
    ] = False,
    interval: Annotated[
        float,
        typer.Option("--interval", help="Delay between actions in seconds"),
    ] = 0.2,
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Run monkey test — random UI interactions with error monitoring.

    Examples:
        u uitree monkey -p "PanelSettings" --count 50 --seed 42
        u uitree monkey -p "PanelSettings" --duration 30
        u uitree monkey -p "PanelSettings" -c "action-btn" --stop-on-error
    """
    from dataclasses import asdict

    from unity_cli.api.uitree_monkey import MonkeyRunner

    context: CLIContext = ctx.obj
    runner = MonkeyRunner(context.client.uitree, context.client.console)
    result = runner.run(
        panel=panel,
        duration=duration,
        count=count,
        seed=seed,
        type_filter=type_filter,
        class_filter=class_filter,
        stop_on_error=stop_on_error,
        interval=interval,
    )

    if _should_json(context, json_flag):
        print_json(asdict(result), None)
    else:
        print_line(
            f"Actions: {result.total_actions}, Errors: {len(result.errors)}, "
            f"Seed: {result.seed}, Duration: {result.duration_ms}ms"
        )
        if result.errors:
            for e in result.errors:
                print_line(f"  Error: {e.get('message', '')}")


# =============================================================================
# snapshot save / diff / list / delete
# =============================================================================


@snapshot_app.command("save")
@handle_cli_errors
def snapshot_save(
    ctx: typer.Context,
    panel: Annotated[str, typer.Option("--panel", "-p", help="Panel name")],
    name: Annotated[str, typer.Option("--name", help="Snapshot name")],
) -> None:
    """Save current UI tree as a named snapshot.

    Examples:
        u uitree snapshot save -p "PanelSettings" --name baseline
    """
    from unity_cli.api.uitree_snapshot import SnapshotStore

    context: CLIContext = ctx.obj
    data = context.client.uitree.dump(panel=panel, format="json")
    path = SnapshotStore().save(name, data)
    print_success(f"Saved snapshot '{name}' to {path}")


@snapshot_app.command("diff")
@handle_cli_errors
def snapshot_diff(
    ctx: typer.Context,
    panel: Annotated[str, typer.Option("--panel", "-p", help="Panel name")],
    name: Annotated[str, typer.Option("--name", help="Baseline snapshot name")],
    json_flag: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Compare current UI tree against a saved snapshot.

    Examples:
        u uitree snapshot diff -p "PanelSettings" --name baseline
    """
    from unity_cli.api.uitree_snapshot import SnapshotStore

    context: CLIContext = ctx.obj
    current = context.client.uitree.dump(panel=panel, format="json")
    result = SnapshotStore().diff(name, current)

    if _should_json(context, json_flag):
        print_json(result, None)
    else:
        _print_diff_result(result)


def _print_diff_result(result: dict[str, Any]) -> None:
    """Print snapshot diff in human-readable format."""
    print_line(f"Baseline: {result['baseline_count']} elements, Current: {result['current_count']} elements")
    for e in result.get("added", []):
        print_line(f"  + {e['name']} ({e['type']})")
    for e in result.get("removed", []):
        print_line(f"  - {e['name']} ({e['type']})")
    for e in result.get("changed", []):
        print_line(f"  ~ {e['name']}: {e['baseline_classes']} -> {e['current_classes']}")
    if not result.get("added") and not result.get("removed") and not result.get("changed"):
        print_success("No changes detected")


@snapshot_app.command("list")
def snapshot_list() -> None:
    """List saved snapshots."""
    from unity_cli.api.uitree_snapshot import SnapshotStore

    names = SnapshotStore().list_names()
    if not names:
        print_line("No snapshots saved")
    else:
        for n in names:
            print_line(n)


@snapshot_app.command("delete")
def snapshot_delete(
    name: Annotated[str, typer.Option("--name", help="Snapshot name to delete")],
) -> None:
    """Delete a saved snapshot."""
    from unity_cli.api.uitree_snapshot import SnapshotStore

    if SnapshotStore().delete(name):
        print_success(f"Deleted snapshot '{name}'")
    else:
        print_line(f"Snapshot '{name}' not found")
