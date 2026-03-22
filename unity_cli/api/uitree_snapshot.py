"""UI tree snapshot storage — save, load, diff tree structures."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

SNAPSHOT_DIR = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "unity-cli" / "uitree-snapshots"

_NAME_RE = re.compile(r"^[\w.\-]+$")


def _flatten_tree(node: dict[str, Any], out: list[dict[str, Any]]) -> None:
    """Recursively flatten a tree into a list of elements."""
    out.append(
        {
            "ref": node.get("ref", ""),
            "name": node.get("name", ""),
            "type": node.get("type", ""),
            "classes": sorted(node.get("classes", [])),
        }
    )
    for child in node.get("children", []):
        _flatten_tree(child, out)


class SnapshotStore:
    """Save and compare UI tree snapshots."""

    def __init__(self, snapshot_dir: Path = SNAPSHOT_DIR) -> None:
        self._dir = snapshot_dir

    def _path(self, name: str) -> Path:
        if not _NAME_RE.fullmatch(name):
            msg = f"Invalid snapshot name: {name!r}"
            raise ValueError(msg)
        return self._dir / f"{name}.json"

    def save(self, name: str, data: dict[str, Any]) -> Path:
        """Save a tree dump as a named snapshot."""
        self._dir.mkdir(parents=True, exist_ok=True)
        path = self._path(name)
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return path

    def load(self, name: str) -> dict[str, Any] | None:
        """Load a saved snapshot. Returns None if not found."""
        path = self._path(name)
        if not path.exists():
            return None
        try:
            result: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
            return result
        except (json.JSONDecodeError, OSError):
            return None

    def diff(self, name: str, current: dict[str, Any]) -> dict[str, Any]:
        """Compare current tree against a saved snapshot."""
        baseline = self.load(name)
        if baseline is None:
            msg = f"Snapshot not found: {name!r}"
            raise FileNotFoundError(msg)

        baseline_elements = _collect_elements(baseline)
        current_elements = _collect_elements(current)

        return _compare_elements(baseline_elements, current_elements)

    def list_names(self) -> list[str]:
        """List all saved snapshot names."""
        if not self._dir.exists():
            return []
        return sorted(p.stem for p in self._dir.glob("*.json"))

    def delete(self, name: str) -> bool:
        """Delete a saved snapshot. Returns True if deleted."""
        path = self._path(name)
        if path.exists():
            path.unlink()
            return True
        return False


def _collect_elements(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten tree data into element list."""
    elements: list[dict[str, Any]] = []
    if "tree" in data:
        _flatten_tree(data["tree"], elements)
    return elements


def _compare_elements(baseline: list[dict[str, Any]], current: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare two flattened element lists by name."""
    baseline_by_name = {e["name"]: e for e in baseline if e["name"]}
    current_by_name = {e["name"]: e for e in current if e["name"]}

    baseline_names = set(baseline_by_name)
    current_names = set(current_by_name)

    added = [current_by_name[n] for n in sorted(current_names - baseline_names)]
    removed = [baseline_by_name[n] for n in sorted(baseline_names - current_names)]
    changed = _find_class_changes(baseline_by_name, current_by_name, baseline_names & current_names)

    return {
        "baseline_count": len(baseline),
        "current_count": len(current),
        "added": added,
        "removed": removed,
        "changed": changed,
    }


def _find_class_changes(
    baseline_by_name: dict[str, dict[str, Any]],
    current_by_name: dict[str, dict[str, Any]],
    common_names: set[str],
) -> list[dict[str, Any]]:
    """Find elements with changed USS classes."""
    changed: list[dict[str, Any]] = []
    for n in sorted(common_names):
        b = baseline_by_name[n]
        c = current_by_name[n]
        if b["classes"] != c["classes"]:
            changed.append(
                {
                    "name": n,
                    "baseline_classes": b["classes"],
                    "current_classes": c["classes"],
                }
            )
    return changed
