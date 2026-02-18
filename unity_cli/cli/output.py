"""Output formatting utilities for Unity CLI.

Supports three modes:
  - PRETTY: Rich-based colored output (TTY default)
  - PLAIN: Tab-separated, no ANSI escapes (pipe default)
  - JSON: Machine-readable JSON

Mode resolution priority:
  --json > --pretty/--no-pretty > UNITY_CLI_JSON/UNITY_CLI_NO_PRETTY/NO_COLOR > isatty()
"""

from __future__ import annotations

import enum
import json
import os
import re
import sys
from dataclasses import dataclass
from typing import Any

from rich.console import Console
from rich.markup import escape
from rich.table import Table
from rich.text import Text

console = Console()
err_console = Console(stderr=True)


# =============================================================================
# Output Mode
# =============================================================================


class OutputMode(enum.Enum):
    PRETTY = "pretty"
    PLAIN = "plain"
    JSON = "json"


@dataclass(frozen=True)
class OutputConfig:
    mode: OutputMode

    @property
    def is_json(self) -> bool:
        return self.mode is OutputMode.JSON

    @property
    def is_plain(self) -> bool:
        return self.mode is OutputMode.PLAIN

    @property
    def is_pretty(self) -> bool:
        return self.mode is OutputMode.PRETTY


def resolve_output_mode(
    json_flag: bool = False,
    pretty_flag: bool | None = None,
) -> OutputMode:
    """Determine output mode from flags, environment, and TTY detection.

    Priority: --json > --pretty/--no-pretty > env vars > isatty()
    """
    if json_flag:
        return OutputMode.JSON

    if pretty_flag is True:
        return OutputMode.PRETTY
    if pretty_flag is False:
        return OutputMode.PLAIN

    # Environment variables
    if os.environ.get("UNITY_CLI_JSON", "").strip() not in ("", "0"):
        return OutputMode.JSON
    if os.environ.get("UNITY_CLI_NO_PRETTY", "").strip() not in ("", "0"):
        return OutputMode.PLAIN
    if os.environ.get("NO_COLOR") is not None:
        return OutputMode.PLAIN

    # TTY detection
    if sys.stdout.isatty():
        return OutputMode.PRETTY
    return OutputMode.PLAIN


def configure_output(mode: OutputMode) -> None:
    """Reconfigure module-level consoles based on output mode."""
    global console, err_console

    if mode is OutputMode.PLAIN or mode is OutputMode.JSON:
        console = Console(highlight=False, no_color=True, soft_wrap=True)
        err_console = Console(stderr=True, highlight=False, no_color=True, soft_wrap=True)
    else:
        console = Console()
        err_console = Console(stderr=True)


def get_output_mode() -> OutputMode:
    """Return the current output mode by inspecting the module console state."""
    if not console.is_terminal and console.no_color:
        # Heuristic: if console was configured as no_color, check JSON via flag
        # The actual mode is tracked in CLIContext; this is a fallback.
        return OutputMode.PLAIN
    return OutputMode.PRETTY


# =============================================================================
# Plain-text helpers
# =============================================================================

_RICH_MARKUP_RE = re.compile(r"\[/?[a-zA-Z][^\]]*\]")


def print_line(text: str) -> None:
    """Print a line, stripping Rich markup in non-PRETTY mode."""
    if console.no_color:
        print(_RICH_MARKUP_RE.sub("", text))
    else:
        console.print(text)


def _print_plain_table(
    headers: list[str],
    rows: list[list[str]],
    title: str | None = None,
) -> None:
    """Print a tab-separated table for pipe-friendly output."""
    if title:
        print(title)
    print("\t".join(headers))
    for row in rows:
        print("\t".join(row))


def filter_fields(data: Any, fields: list[str] | None) -> Any:
    """Filter data to include only specified fields.

    Args:
        data: Dict, list of dicts, or other data
        fields: Field names to include. None or empty returns all.

    Returns:
        Filtered data with only specified fields.
    """
    if not fields:
        return data

    # Convert to set for O(1) lookup
    fields_set = set(fields)

    if isinstance(data, dict):
        return {k: v for k, v in data.items() if k in fields_set}
    if isinstance(data, list):
        # Reuse the same set for all items
        return [_filter_dict(item, fields_set) for item in data]
    return data


def _filter_dict(item: Any, fields_set: set[str]) -> Any:
    """Internal helper to filter a single item with pre-computed set."""
    if isinstance(item, dict):
        return {k: v for k, v in item.items() if k in fields_set}
    return item


def print_json(data: Any, fields: list[str] | None = None) -> None:
    """Print data as JSON with optional field filtering.

    Args:
        data: Data to output
        fields: Fields to include (None for all)
    """
    filtered = filter_fields(data, fields)
    if console.no_color:
        print(json.dumps(filtered, ensure_ascii=False, indent=2))
    else:
        console.print_json(json.dumps(filtered, ensure_ascii=False))


def print_error(message: str, code: str | None = None) -> None:
    """Print error message to stderr.

    Args:
        message: Error message (will be escaped to prevent markup injection)
        code: Optional error code
    """
    if err_console.no_color:
        print(f"Error: {message}", file=sys.stderr)
        if code:
            print(f"Code: {code}", file=sys.stderr)
        return

    text = Text()
    text.append("Error: ", style="bold red")
    text.append(escape(message))  # Escape untrusted content
    err_console.print(text)

    if code:
        code_text = Text()
        code_text.append("Code: ", style="dim")
        code_text.append(escape(code), style="yellow")  # Escape untrusted content
        err_console.print(code_text)


def print_validation_error(message: str, help_command: str) -> None:
    """Print validation error with --help guidance.

    Args:
        message: Error message
        help_command: Command to show help for (e.g., "u scene load")
    """
    print_error(f"{message}. Run '{help_command} --help' for usage.")


def print_success(message: str) -> None:
    """Print success message.

    Args:
        message: Success message
    """
    if console.no_color:
        print(f"[OK] {message}")
        return

    text = Text()
    text.append("[OK] ", style="bold green")
    text.append(message)
    console.print(text)


def print_warning(message: str) -> None:
    """Print warning message.

    Args:
        message: Warning message
    """
    if console.no_color:
        print(f"[WARN] {message}")
        return

    text = Text()
    text.append("[WARN] ", style="bold yellow")
    text.append(message)
    console.print(text)


def print_info(message: str) -> None:
    """Print info message.

    Args:
        message: Info message
    """
    if console.no_color:
        print(f"[INFO] {message}")
        return

    text = Text()
    text.append("[INFO] ", style="bold blue")
    text.append(message)
    console.print(text)


def print_instances_table(instances: list[dict[str, Any]]) -> None:
    """Print Unity instances as a formatted table."""
    if not instances:
        print_line("No Unity instances connected")
        return

    # Detect duplicate project names to decide whether to show path
    project_names = [inst.get("project_name", "") for inst in instances]
    has_duplicates = len(project_names) != len(set(project_names))
    cwd = os.getcwd()

    if console.no_color:
        headers = ["#", "Project"]
        if has_duplicates:
            headers.append("Path")
        headers.extend(["Version", "Status", "Default"])

        rows: list[list[str]] = []
        for inst in instances:
            ref_id = str(inst.get("ref_id", ""))
            project = inst.get("project_name", inst.get("instance_id", "Unknown"))
            version = inst.get("unity_version", "Unknown")
            status = inst.get("status", "unknown")
            is_default = "*" if inst.get("is_default") else ""

            row = [ref_id, project]
            if has_duplicates:
                row.append(os.path.relpath(inst.get("instance_id", ""), cwd))
            row.extend([version, status, is_default])
            rows.append(row)

        _print_plain_table(headers, rows, f"Connected Instances ({len(instances)})")
        return

    table = Table(title=f"Connected Instances ({len(instances)})")
    table.add_column("#", style="dim", justify="right", no_wrap=True)
    table.add_column("Project", style="cyan", no_wrap=True)
    if has_duplicates:
        table.add_column("Path (-i)", style="dim")
    table.add_column("Unity Version", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Default", justify="center")

    for inst in instances:
        ref_id = str(inst.get("ref_id", ""))
        project = escape(inst.get("project_name", inst.get("instance_id", "Unknown")))
        instance_id = inst.get("instance_id", "")
        version = escape(inst.get("unity_version", "Unknown"))
        status = inst.get("status", "unknown")
        is_default = "[green]*[/green]" if inst.get("is_default") else ""

        status_style = {
            "ready": "green",
            "busy": "yellow",
            "reloading": "magenta",
            "disconnected": "red",
        }.get(status.lower(), "dim")

        row_items: list[str | Text] = [ref_id, project]
        if has_duplicates:
            rel_path = os.path.relpath(instance_id, cwd)
            row_items.append(escape(rel_path))
        row_items.extend([version, Text(escape(status), style=status_style), is_default])

        table.add_row(*row_items)

    console.print(table)


def print_logs_table(logs: list[dict[str, Any]]) -> None:
    """Print console logs as a formatted table."""
    if not logs:
        print_line("No logs found")
        return

    if console.no_color:
        headers = ["Type", "Message"]
        rows: list[list[str]] = []
        for log in logs:
            log_type = log.get("type", "log").upper()
            message = log.get("message", "")
            if len(message) > 200:
                message = message[:197] + "..."
            rows.append([log_type, message])
        _print_plain_table(headers, rows, f"Console Logs ({len(logs)})")
        return

    table = Table(title=f"Console Logs ({len(logs)})")
    table.add_column("Type", style="bold", width=8)
    table.add_column("Message", overflow="fold")

    type_styles = {
        "error": "red",
        "exception": "red bold",
        "warning": "yellow",
        "log": "white",
        "assert": "magenta",
    }

    for log in logs:
        log_type = log.get("type", "log").lower()
        message = log.get("message", "")

        if len(message) > 200:
            message = message[:197] + "..."

        style = type_styles.get(log_type, "dim")
        table.add_row(
            Text(log_type.upper(), style=style),
            escape(message),
        )

    console.print(table)


def print_hierarchy_table(items: list[dict[str, Any]], show_components: bool = False) -> None:
    """Print scene hierarchy as a formatted table."""
    if not items:
        print_line("No GameObjects in hierarchy")
        return

    if console.no_color:
        headers = ["Name", "ID", "Children"]
        if show_components:
            headers.append("Components")

        rows: list[list[str]] = []
        for item in items:
            depth = item.get("depth", 0)
            indent = "  " * depth
            name = f"{indent}{item.get('name', 'Unknown')}"
            instance_id = str(item.get("instanceID", ""))
            child_count = str(item.get("childCount", 0))
            row = [name, instance_id, child_count]
            if show_components:
                components = item.get("components", [])
                comp_str = ", ".join(components[:3])
                row.append(comp_str + ("..." if len(components) > 3 else ""))
            rows.append(row)

        _print_plain_table(headers, rows, f"Scene Hierarchy ({len(items)} objects)")
        return

    table = Table(title=f"Scene Hierarchy ({len(items)} objects)")
    table.add_column("Name", style="cyan")
    table.add_column("ID", style="dim", justify="right")
    table.add_column("Children", justify="center")
    if show_components:
        table.add_column("Components", style="green")

    for item in items:
        depth = item.get("depth", 0)
        indent = "  " * depth
        name = escape(f"{indent}{item.get('name', 'Unknown')}")
        instance_id = str(item.get("instanceID", ""))
        child_count = str(item.get("childCount", 0))

        row = [name, instance_id, child_count]
        if show_components:
            components = item.get("components", [])
            comp_str = ", ".join(escape(c) for c in components[:3])
            row.append(comp_str + ("..." if len(components) > 3 else ""))

        table.add_row(*row)

    console.print(table)


def print_components_table(components: list[dict[str, Any]]) -> None:
    """Print component list as a formatted table."""
    if not components:
        print_line("No components found")
        return

    if console.no_color:
        headers = ["Type", "Enabled", "ID"]
        rows: list[list[str]] = []
        for comp in components:
            comp_type = comp.get("type", "Unknown")
            enabled = "Yes" if comp.get("enabled", True) else "No"
            instance_id = str(comp.get("instanceID", ""))
            rows.append([comp_type, enabled, instance_id])
        _print_plain_table(headers, rows, f"Components ({len(components)})")
        return

    table = Table(title=f"Components ({len(components)})")
    table.add_column("Type", style="cyan")
    table.add_column("Enabled", justify="center")
    table.add_column("ID", style="dim", justify="right")

    for comp in components:
        comp_type = escape(comp.get("type", "Unknown"))
        enabled = comp.get("enabled", True)
        instance_id = str(comp.get("instanceID", ""))

        enabled_display = "[green]Yes[/green]" if enabled else "[red]No[/red]"

        table.add_row(comp_type, enabled_display, instance_id)

    console.print(table)


def print_test_results_table(results: list[dict[str, Any]]) -> None:
    """Print test results as a formatted table."""
    if not results:
        print_line("No test results")
        return

    passed = sum(1 for r in results if r.get("result") == "Passed")
    failed = sum(1 for r in results if r.get("result") == "Failed")
    skipped = sum(1 for r in results if r.get("result") == "Skipped")

    title = f"Test Results (Passed: {passed}, Failed: {failed}, Skipped: {skipped})"

    if console.no_color:
        headers = ["Test", "Result", "Duration"]
        rows: list[list[str]] = []
        for test in results:
            name = test.get("name", "Unknown")
            result = test.get("result", "Unknown")
            duration = test.get("duration", 0)
            duration_str = f"{duration:.3f}s" if isinstance(duration, float) else str(duration)
            rows.append([name, result, duration_str])
        _print_plain_table(headers, rows, title)
        return

    table = Table(title=title)
    table.add_column("Test", style="cyan", overflow="fold")
    table.add_column("Result", justify="center")
    table.add_column("Duration", justify="right")

    result_styles = {
        "Passed": "green",
        "Failed": "red",
        "Skipped": "yellow",
        "Inconclusive": "magenta",
    }

    for test in results:
        name = escape(test.get("name", "Unknown"))
        result = test.get("result", "Unknown")
        duration = test.get("duration", 0)

        style = result_styles.get(result, "dim")
        duration_str = f"{duration:.3f}s" if isinstance(duration, float) else str(duration)

        table.add_row(name, Text(escape(result), style=style), duration_str)

    console.print(table)


def print_key_value(data: dict[str, Any], title: str | None = None) -> None:
    """Print dict as key-value pairs."""
    if console.no_color:
        if title:
            print(title)
        for key, value in data.items():
            print(f"  {key}: {value}")
        return

    if title:
        console.print(f"[bold]{escape(title)}[/bold]")

    for key, value in data.items():
        console.print(f"  [cyan]{escape(str(key))}:[/cyan] {escape(str(value))}")
