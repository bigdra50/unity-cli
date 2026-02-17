"""Integration test fixtures.

Requires a running Relay Server and Unity Editor.
Tests are skipped automatically when the environment is unavailable.

Environment variables:
    UNITY_TEST_INSTANCE: Unity instance name (default: "TestProject")
"""

from __future__ import annotations

import os
import uuid
from typing import Any

import pytest

from unity_cli.api import (
    ConsoleAPI,
    EditorAPI,
    GameObjectAPI,
    SceneAPI,
    UITreeAPI,
)
from unity_cli.client import RelayConnection
from unity_cli.exceptions import ConnectionError

INSTANCE = os.environ.get("UNITY_TEST_INSTANCE", "TestProject")


def _try_connect() -> RelayConnection | None:
    """Attempt to connect to the Relay Server."""
    conn = RelayConnection(instance=INSTANCE, timeout=3.0)
    try:
        EditorAPI(conn).get_state()
        return conn
    except (ConnectionError, OSError):
        return None


@pytest.fixture(scope="session")
def conn() -> RelayConnection:
    """Session-scoped relay connection."""
    c = _try_connect()
    if c is None:
        pytest.skip("Relay Server or Unity Editor not available")
    return c


@pytest.fixture(scope="session")
def editor(conn: RelayConnection) -> EditorAPI:
    return EditorAPI(conn)


@pytest.fixture(scope="session")
def scene(conn: RelayConnection) -> SceneAPI:
    return SceneAPI(conn)


@pytest.fixture(scope="session")
def gameobject(conn: RelayConnection) -> GameObjectAPI:
    return GameObjectAPI(conn)


@pytest.fixture(scope="session")
def console(conn: RelayConnection) -> ConsoleAPI:
    return ConsoleAPI(conn)


@pytest.fixture(scope="session")
def uitree(conn: RelayConnection) -> UITreeAPI:
    return UITreeAPI(conn)


@pytest.fixture()
def temp_gameobject(gameobject: GameObjectAPI):
    """Factory fixture: creates temporary GameObjects with auto-cleanup.

    Yields a callable that creates a GameObject with a UUID-based unique name.
    All created objects are deleted via instance_id on teardown.

    Usage::

        name, result = temp_gameobject()
        name, result = temp_gameobject("_suffix")
    """
    created_ids: list[int] = []

    def _create(suffix: str = "") -> tuple[str, dict[str, Any]]:
        name = f"_Test_{uuid.uuid4().hex[:8]}{suffix}"
        result = gameobject.create(name=name)
        created_ids.append(result["gameObject"]["instanceID"])
        return name, result

    yield _create

    for instance_id in created_ids:
        try:
            gameobject.delete(instance_id=instance_id)
        except Exception:
            pass
