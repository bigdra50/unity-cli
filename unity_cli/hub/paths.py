"""Platform-specific path resolution for Unity Hub and Editor."""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class PlatformPaths:
    """Platform-specific Unity paths."""

    hub_cli: Path | None
    editor_base: Path


@dataclass(frozen=True)
class InstalledEditor:
    """Installed Unity Editor info."""

    version: str
    path: Path


def _get_platform_hub_candidates() -> list[Path]:
    """Platform-specific Hub CLI locations (ordered by priority)."""
    if sys.platform == "darwin":
        return [
            Path("/Applications/Unity Hub.app/Contents/MacOS/Unity Hub"),
            Path.home() / "Applications/Unity Hub.app/Contents/MacOS/Unity Hub",
        ]
    elif sys.platform == "win32":
        localappdata = os.environ.get("LOCALAPPDATA", "")
        candidates = [
            Path(r"C:\Program Files\Unity Hub\Unity Hub.exe"),
        ]
        if localappdata:
            candidates.append(Path(localappdata) / "Programs/Unity Hub/Unity Hub.exe")
        return candidates
    else:  # Linux
        return [
            Path("/opt/unityhub/unityhub"),
            Path.home() / "Unity/Hub/UnityHub.AppImage",
            Path.home() / ".local/share/applications/unityhub.AppImage",
        ]


def _get_platform_editor_base() -> Path:
    """Platform-specific editor installation base directory."""
    if sys.platform == "darwin":
        return Path("/Applications/Unity/Hub/Editor")
    elif sys.platform == "win32":
        return Path(r"C:\Program Files\Unity\Hub\Editor")
    else:  # Linux
        return Path.home() / "Unity/Hub/Editor"


def _get_editor_binary_path(editor_base: Path, version: str) -> Path:
    """Get the Unity Editor binary path for a version."""
    if sys.platform == "darwin":
        return editor_base / version / "Unity.app/Contents/MacOS/Unity"
    elif sys.platform == "win32":
        return editor_base / version / "Editor/Unity.exe"
    else:  # Linux
        return editor_base / version / "Editor/Unity"


@lru_cache(maxsize=1)
def locate_hub_cli() -> Path | None:
    """Locate Hub CLI with fallback strategy.

    Search order:
    1. UNITY_HUB_PATH environment variable
    2. PATH lookup (shutil.which)
    3. Platform-specific known locations
    """
    # 1. Environment variable override
    if env_path := os.environ.get("UNITY_HUB_PATH"):
        path = Path(env_path)
        if path.exists():
            return path

    # 2. PATH lookup
    which_names = ["unityhub", "Unity Hub"]
    for name in which_names:
        if which_path := shutil.which(name):
            return Path(which_path)

    # 3. Platform-specific known locations
    for candidate in _get_platform_hub_candidates():
        if candidate.exists():
            return candidate

    return None


@lru_cache(maxsize=1)
def get_platform_paths() -> PlatformPaths:
    """Get platform-specific Unity paths."""
    return PlatformPaths(
        hub_cli=locate_hub_cli(),
        editor_base=_get_platform_editor_base(),
    )


def get_installed_editors() -> list[InstalledEditor]:
    """List installed Unity editors from filesystem.

    Scans the editor installation directory for valid Unity installations.
    """
    paths = get_platform_paths()
    editors: list[InstalledEditor] = []

    if not paths.editor_base.exists():
        return editors

    for version_dir in paths.editor_base.iterdir():
        if not version_dir.is_dir():
            continue

        binary_path = _get_editor_binary_path(paths.editor_base, version_dir.name)
        if binary_path.exists():
            editors.append(
                InstalledEditor(
                    version=version_dir.name,
                    path=binary_path,
                )
            )

    # Sort by version (newest first, simple string sort)
    editors.sort(key=lambda e: e.version, reverse=True)
    return editors


def find_editor_by_version(version: str) -> InstalledEditor | None:
    """Find an installed editor by version string."""
    editors = get_installed_editors()
    for editor in editors:
        if editor.version == version:
            return editor
    return None
