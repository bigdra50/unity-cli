#!/usr/bin/env python3
"""Bump version across pyproject.toml and UnityBridge/package.json.

Usage:
    python scripts/bump-version.py 3.4.0          # set explicit version
    python scripts/bump-version.py patch           # 3.3.2 -> 3.3.3
    python scripts/bump-version.py minor           # 3.3.2 -> 3.4.0
    python scripts/bump-version.py major           # 3.3.2 -> 4.0.0
    python scripts/bump-version.py patch --tag     # bump + git tag
    python scripts/bump-version.py patch --dry-run # preview only
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"
PACKAGE_JSON = ROOT / "UnityBridge" / "package.json"
RELAY_INIT = ROOT / "relay" / "__init__.py"

VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
BUMP_TYPES = ("patch", "minor", "major")


def read_current_version() -> str:
    """
    Retrieve the current project version declared in pyproject.toml.
    
    Returns:
        version (str): The semantic version string from the `project.version` field (e.g., "1.2.3").
    """
    data = tomllib.loads(PYPROJECT.read_text())
    return data["project"]["version"]


def compute_next_version(current: str, spec: str) -> str:
    """
    Determine the next semantic version based on the current version and a specification.
    
    If `spec` is a concrete version string (format X.Y.Z), it is returned unchanged. If `spec` is one of "patch", "minor", or "major", compute the next version by incrementing the corresponding component:
    - "patch": increment patch
    - "minor": increment minor and reset patch to 0
    - "major": increment major and reset minor and patch to 0
    
    Parameters:
        current (str): Current version in the form "X.Y.Z".
        spec (str): Either a concrete version "X.Y.Z" or a bump type ("patch", "minor", "major").
    
    Returns:
        str: The next version string (format "X.Y.Z").
    
    Side effects:
        Prints an error and exits the process with status 1 if `spec` is neither a valid version nor a supported bump type.
    """
    if VERSION_RE.match(spec):
        return spec

    if spec not in BUMP_TYPES:
        print(f"Error: '{spec}' is not a valid version or bump type ({', '.join(BUMP_TYPES)})")
        sys.exit(1)

    major, minor, patch = (int(x) for x in current.split("."))
    if spec == "patch":
        patch += 1
    elif spec == "minor":
        minor += 1
        patch = 0
    elif spec == "major":
        major += 1
        minor = 0
        patch = 0
    return f"{major}.{minor}.{patch}"


def update_pyproject(version: str) -> None:
    """
    Update the version value in pyproject.toml to the provided version.
    
    Replaces the first occurrence of a top-level `version = "..."` entry in the file while preserving surrounding formatting and writes the updated content back to pyproject.toml.
    
    Parameters:
        version (str): New semantic version string (e.g., "1.2.3").
    """
    text = PYPROJECT.read_text()
    updated = re.sub(
        r'^(version\s*=\s*")[^"]+(")',
        rf"\g<1>{version}\2",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    PYPROJECT.write_text(updated)


def update_package_json(version: str) -> None:
    """
    Update the UnityBridge/package.json file's version field on disk.
    
    Writes the package.json JSON with the `version` set to `version`, using 2-space indentation and a trailing newline.
    
    Parameters:
    	version (str): Semantic version string to write into the package.json `version` field.
    """
    data = json.loads(PACKAGE_JSON.read_text())
    data["version"] = version
    PACKAGE_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def cleanup_relay_init() -> bool:
    """
    Remove a top-level __version__ assignment from relay/__init__.py if present.
    
    This edits relay/__init__.py in place when a line like `__version__ = "x.y.z"` exists.
    
    Returns:
        bool: `True` if a `__version__` assignment line was removed, `False` otherwise.
    """
    if not RELAY_INIT.exists():
        return False
    text = RELAY_INIT.read_text()
    cleaned = re.sub(r"^__version__\s*=\s*['\"].*['\"]\s*\n", "", text, flags=re.MULTILINE)
    if cleaned != text:
        RELAY_INIT.write_text(cleaned)
        return True
    return False


def create_tag(version: str) -> None:
    """
    Create a git tag named `v{version}` in the repository root.
    
    Runs `git tag v{version}` in the repository root and prints the created tag. May raise subprocess.CalledProcessError if the git command fails.
    
    Parameters:
        version (str): Semantic version string (e.g., "1.2.3") to tag without the leading "v".
    """
    tag = f"v{version}"
    subprocess.run(["git", "tag", tag], check=True, cwd=ROOT)
    print(f"Created tag: {tag}")


def main() -> None:
    """
    Run the version bump command-line workflow.
    
    Parses command-line arguments for an explicit version or bump type and optional flags --tag and --dry-run, computes the next semantic version from pyproject.toml, and displays the planned changes. Unless --dry-run is used, updates pyproject.toml and UnityBridge/package.json with the new version, performs a one-time removal of a __version__ line from relay/__init__.py if present, and, if --tag is specified, creates a git tag `v<version>`.
    """
    parser = argparse.ArgumentParser(description="Bump project version")
    parser.add_argument("version", help="Explicit version (3.4.0) or bump type (patch/minor/major)")
    parser.add_argument("--tag", action="store_true", help="Create git tag after bumping")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()

    current = read_current_version()
    next_ver = compute_next_version(current, args.version)

    print(f"Current version: {current}")
    print(f"Next version:    {next_ver}")
    print()
    print(f"  pyproject.toml:          {current} -> {next_ver}")
    print(f"  UnityBridge/package.json: {current} -> {next_ver}")

    if args.dry_run:
        print("\n(dry-run: no files changed)")
        return

    update_pyproject(next_ver)
    update_package_json(next_ver)
    print("\nFiles updated.")

    if cleanup_relay_init():
        print("Removed __version__ from relay/__init__.py (one-time migration)")

    if args.tag:
        create_tag(next_ver)


if __name__ == "__main__":
    main()