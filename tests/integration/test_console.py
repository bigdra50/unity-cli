"""Integration tests for ConsoleAPI commands."""

from __future__ import annotations

from unity_cli.api import ConsoleAPI


class TestConsoleGet:
    def test_get_returns_entries(self, console: ConsoleAPI) -> None:
        actual = console.get()

        assert "entries" in actual
        assert isinstance(actual["entries"], list)

    def test_get_with_count_limits_results(self, console: ConsoleAPI) -> None:
        actual = console.get(count=3)

        assert len(actual["entries"]) <= 3

    def test_get_with_types_filter(self, console: ConsoleAPI) -> None:
        actual = console.get(types=["error"])

        for entry in actual["entries"]:
            assert entry["type"] in ("error", "exception", "assert")

    def test_get_simple_format(self, console: ConsoleAPI) -> None:
        actual = console.get(format="simple")

        assert "entries" in actual


class TestConsoleClear:
    def test_clear_succeeds(self, console: ConsoleAPI) -> None:
        actual = console.clear()

        assert actual.get("success") is True or "message" in actual
