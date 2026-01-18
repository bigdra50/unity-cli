"""Unity Editor launcher."""

from __future__ import annotations

import subprocess
from pathlib import Path


def launch_editor(
    editor_path: Path,
    project_path: Path,
    wait: bool = False,
) -> subprocess.Popen[bytes] | None:
    """Launch Unity Editor with project.

    Args:
        editor_path: Path to Unity executable.
        project_path: Path to Unity project.
        wait: If True, wait for editor to close.

    Returns:
        Popen object if not waiting, None if waiting.
    """
    cmd = [
        str(editor_path),
        "-projectPath",
        str(project_path.resolve()),
    ]

    if wait:
        subprocess.run(cmd, check=False)
        return None
    else:
        return subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def launch_editor_with_version(
    version: str,
    project_path: Path,
    wait: bool = False,
) -> subprocess.Popen[bytes] | None:
    """Launch Unity Editor by version.

    Convenience function that looks up the editor path by version.

    Args:
        version: Unity version string (e.g., "2022.3.10f1").
        project_path: Path to Unity project.
        wait: If True, wait for editor to close.

    Returns:
        Popen object if not waiting, None if waiting.

    Raises:
        EditorNotFoundError: If editor version not installed.
    """
    from unity_cli.exceptions import EditorNotFoundError
    from unity_cli.hub.paths import find_editor_by_version

    editor = find_editor_by_version(version)
    if editor is None:
        raise EditorNotFoundError(
            f"Unity {version} is not installed",
            code="EDITOR_NOT_FOUND",
        )

    return launch_editor(editor.path, project_path, wait)
