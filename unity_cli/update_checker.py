"""Check for CLI updates via GitHub Releases API."""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

CACHE_DIR = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "unity-cli"
CACHE_FILE = CACHE_DIR / "update-check.json"
CHECK_INTERVAL = 86400  # 24 hours
RELEASES_URL = "https://api.github.com/repos/bigdra50/unity-cli/releases/latest"
FETCH_TIMEOUT = 3  # seconds


def get_latest_version_cached() -> str | None:
    """Return cached latest version if TTL is still valid, else None."""
    try:
        if not CACHE_FILE.exists():
            return None
        data = json.loads(CACHE_FILE.read_text())
        if time.time() - data.get("checked_at", 0) > CHECK_INTERVAL:
            return None
        version: str | None = data.get("latest_version")
        return version
    except (json.JSONDecodeError, OSError):
        return None


def _fetch_latest_version() -> None:
    """Fetch latest version from GitHub API and write to cache (blocking)."""
    try:
        req = Request(RELEASES_URL, headers={"Accept": "application/vnd.github.v3+json"})
        with urlopen(req, timeout=FETCH_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        tag = data.get("tag_name", "")
        version = tag.lstrip("v")
        if not version:
            return
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps({"latest_version": version, "checked_at": time.time()}))
    except (URLError, OSError, json.JSONDecodeError, KeyError):
        pass


def start_update_check() -> None:
    """Start background check for updates (daemon thread, non-blocking)."""
    cached = get_latest_version_cached()
    if cached is not None:
        return
    t = threading.Thread(target=_fetch_latest_version, daemon=True)
    t.start()


def get_update_message(current: str) -> str | None:
    """Return an update notification message if a newer version exists."""
    latest = get_latest_version_cached()
    if not latest or not current:
        return None
    try:
        from packaging.version import Version

        if Version(latest) > Version(current):
            return f"Update available: {current} -> {latest}\nRun 'uv tool install --force unity-cli' to update"
    except ImportError:
        # packaging not available; fall back to tuple comparison
        def _parse_version(v: str) -> tuple[int, ...]:
            return tuple(int(x) for x in v.split("."))

        try:
            if _parse_version(latest) > _parse_version(current):
                return f"Update available: {current} -> {latest}\nRun 'uv tool install --force unity-cli' to update"
        except (ValueError, TypeError):
            pass
    return None
