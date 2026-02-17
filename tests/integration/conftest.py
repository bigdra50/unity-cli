"""Integration test fixtures.

Requires a running Relay Server and Unity Editor (TestProject).
Tests are skipped automatically when the environment is unavailable.
"""

from __future__ import annotations

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

INSTANCE = "TestProject"


def _try_connect() -> RelayConnection | None:
    """Attempt to connect to the Relay Server."""
    conn = RelayConnection(instance=INSTANCE, timeout=3.0)
    try:
        EditorAPI(conn).get_state()
        return conn
    except (ConnectionError, OSError):
        return None


_conn_cache: RelayConnection | None = None
_conn_checked = False


def _get_connection() -> RelayConnection | None:
    global _conn_cache, _conn_checked
    if not _conn_checked:
        _conn_cache = _try_connect()
        _conn_checked = True
    return _conn_cache


@pytest.fixture(scope="session")
def conn() -> RelayConnection:
    """Session-scoped relay connection to TestProject."""
    c = _get_connection()
    if c is None:
        pytest.skip("Relay Server or TestProject not available")
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
