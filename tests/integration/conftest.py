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


@pytest.fixture(scope="session")
def conn() -> RelayConnection:
    """Session-scoped relay connection to TestProject."""
    c = _try_connect()
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
