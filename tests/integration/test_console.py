"""Integration tests for ConsoleAPI commands."""

from __future__ import annotations

import pytest

from unity_cli.api import ConsoleAPI

pytestmark = pytest.mark.integration


class TestConsoleGet:
    def test_get_returns_entries(self, console: ConsoleAPI) -> None:
        response = console.get(count=10)

        assert "entries" in response
        assert isinstance(response["entries"], list)

    def test_get_with_count_limits_results(self, console: ConsoleAPI) -> None:
        response = console.get(count=3)

        assert len(response["entries"]) <= 3

    def test_get_with_types_filter(self, console: ConsoleAPI) -> None:
        response = console.get(types=["error"], count=10)

        for entry in response["entries"]:
            assert entry["type"] in ("error", "exception", "assert")

    def test_get_simple_format(self, console: ConsoleAPI) -> None:
        response = console.get(format="simple", count=10)

        assert "entries" in response


class TestConsoleClear:
    def test_clear_succeeds(self, console: ConsoleAPI) -> None:
        response = console.clear()

        assert response["success"] is True
