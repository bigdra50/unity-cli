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
    data = tomllib.loads(PYPROJECT.read_text())
    return data["project"]["version"]


def compute_next_version(current: str, spec: str) -> str:
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
    data = json.loads(PACKAGE_JSON.read_text())
    data["version"] = version
    PACKAGE_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def cleanup_relay_init() -> bool:
    """Remove __version__ line from relay/__init__.py if present. Returns True if removed."""
    if not RELAY_INIT.exists():
        return False
    text = RELAY_INIT.read_text()
    cleaned = re.sub(r"^__version__\s*=\s*['\"].*['\"]\s*\n", "", text, flags=re.MULTILINE)
    if cleaned != text:
        RELAY_INIT.write_text(cleaned)
        return True
    return False


def create_tag(version: str) -> None:
    tag = f"v{version}"
    subprocess.run(["git", "tag", tag], check=True, cwd=ROOT)
    print(f"Created tag: {tag}")


def main() -> None:
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
