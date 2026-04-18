"""Root test configuration.

Provides shared fixtures and automatic marker assignment.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_conn() -> MagicMock:
    """Create a bare MagicMock relay connection.

    Tests that need custom return values should override this fixture
    locally (e.g. test_dynamic_api.py).
    """
    return MagicMock()


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Auto-mark integration tests and reorder: unit first, integration last."""
    integration_dir = Path(__file__).parent / "integration"

    unit_items: list[pytest.Item] = []
    integration_items: list[pytest.Item] = []

    for item in items:
        if Path(item.fspath).is_relative_to(integration_dir):
            item.add_marker(pytest.mark.integration)
            integration_items.append(item)
        else:
            unit_items.append(item)

    items[:] = unit_items + integration_items
