"""API schema cache — stores per-Unity-version schema as JSON."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

CACHE_DIR = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "unity-cli" / "api-schema"

_VERSION_RE = re.compile(r"^[\w.\-]+$")


class SchemaCache:
    """Read/write API schema cache keyed by Unity version."""

    def __init__(self, cache_dir: Path = CACHE_DIR) -> None:
        self._dir = cache_dir

    def _path(self, version: str) -> Path:
        if not _VERSION_RE.fullmatch(version):
            msg = f"Invalid version string: {version!r}"
            raise ValueError(msg)
        return self._dir / f"{version}.json"

    def get(self, version: str) -> dict[str, Any] | None:
        """Return cached schema or None if not cached."""
        path = self._path(version)
        if not path.exists():
            return None
        try:
            data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
            return data
        except (json.JSONDecodeError, OSError):
            return None

    def put(self, version: str, schema: dict[str, Any]) -> None:
        """Write schema to cache."""
        self._dir.mkdir(parents=True, exist_ok=True)
        path = self._path(version)
        path.write_text(json.dumps(schema, ensure_ascii=False), encoding="utf-8")

    def has(self, version: str) -> bool:
        """Check if schema is cached for this version."""
        return self._path(version).exists()
