"""
Status File Reader

Reads Unity instance status from file-based notifications.
Used as fallback when TCP status notification fails.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StatusFileContent:
    """Parsed content of a status file"""

    instance_id: str
    project_name: str
    unity_version: str
    status: str  # "ready" or "reloading"
    relay_host: str
    relay_port: int
    timestamp: datetime
    seq: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StatusFileContent:
        timestamp_str = data.get("timestamp", "")
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            timestamp = datetime.now(UTC)

        return cls(
            instance_id=data.get("instance_id", ""),
            project_name=data.get("project_name", ""),
            unity_version=data.get("unity_version", ""),
            status=data.get("status", "ready"),
            relay_host=data.get("relay_host", "127.0.0.1"),
            relay_port=data.get("relay_port", 6500),
            timestamp=timestamp,
            seq=data.get("seq", 0),
        )


def get_status_dir() -> Path:
    """Get status file directory (~/.unity-bridge, overridable via UNITY_BRIDGE_STATUS_DIR)"""
    env_dir = os.environ.get("UNITY_BRIDGE_STATUS_DIR")
    if env_dir:
        return Path(env_dir)
    return Path.home() / ".unity-bridge"


def compute_instance_hash(instance_id: str) -> str:
    """Compute 8-char hash (SHA1 first 8 hex digits) from instance ID"""
    hash_bytes = hashlib.sha1(instance_id.encode("utf-8")).digest()
    return hash_bytes[:4].hex()


def get_status_file_path(instance_id: str) -> Path:
    """Get path to status file for an instance (status-{hash}.json format)"""
    hash_str = compute_instance_hash(instance_id)
    return get_status_dir() / f"status-{hash_str}.json"


def read_status_file(instance_id: str) -> StatusFileContent | None:
    """
    Read status file for a specific instance.

    Returns None if file doesn't exist or is invalid.
    """
    try:
        file_path = get_status_file_path(instance_id)
        if not file_path.exists():
            return None

        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        return StatusFileContent.from_dict(data)
    except (json.JSONDecodeError, OSError) as e:
        logger.debug(f"Failed to read status file for {instance_id}: {e}")
        return None


def read_all_status_files() -> list[StatusFileContent]:
    """
    Read all status files in the status directory.

    Returns list of status file contents, sorted by timestamp (newest first).
    """
    status_dir = get_status_dir()
    if not status_dir.exists():
        return []

    results: list[StatusFileContent] = []
    for file_path in status_dir.glob("status-*.json"):
        try:
            with file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            results.append(StatusFileContent.from_dict(data))
        except (json.JSONDecodeError, OSError) as e:
            logger.debug(f"Failed to read status file {file_path}: {e}")

    # Sort by timestamp, newest first
    results.sort(key=lambda x: x.timestamp, reverse=True)
    return results


def is_any_instance_reloading(query: str, max_age_seconds: float = 120.0) -> bool:
    """Check if any reloading instance matches a query (project_name, path suffix, or exact id).

    Unlike is_instance_reloading which requires exact instance_id for hash lookup,
    this scans all status files. Use when instance_id may be a ref_id or project name.
    """
    if is_instance_reloading(query, max_age_seconds):
        return True

    for status in read_all_status_files():
        if status.status != "reloading":
            continue
        age = (datetime.now(UTC) - status.timestamp.replace(tzinfo=UTC)).total_seconds()
        if age > max_age_seconds:
            continue
        if status.project_name == query:
            return True
        if status.instance_id.endswith("/" + query) or status.instance_id.endswith("\\" + query):
            return True
    return False


def is_instance_reloading(instance_id: str, max_age_seconds: float = 120.0) -> bool:
    """
    Check if an instance is currently reloading.

    Args:
        instance_id: Instance ID to check
        max_age_seconds: Maximum age of status file to consider valid

    Returns:
        True if status file indicates reloading and is recent enough
    """
    status = read_status_file(instance_id)
    if status is None:
        return False

    if status.status != "reloading":
        return False

    # Check if status is too old (likely stale)
    age = (datetime.now(UTC) - status.timestamp.replace(tzinfo=UTC)).total_seconds()
    if age > max_age_seconds:
        logger.debug(f"Status file for {instance_id} is stale ({age:.1f}s old)")
        return False

    return True
