"""Tests for unity_cli/api/uitree_monkey.py"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from unity_cli.api.uitree_monkey import MonkeyRunner


@pytest.fixture
def mock_uitree() -> MagicMock:
    uitree = MagicMock()
    uitree.query.return_value = {
        "matches": [
            {"ref": "ref_1", "name": "Btn1", "type": "VisualElement"},
            {"ref": "ref_2", "name": "Btn2", "type": "VisualElement"},
            {"ref": "ref_3", "name": "Btn3", "type": "VisualElement"},
        ]
    }
    uitree.click.return_value = {}
    return uitree


@pytest.fixture
def mock_console() -> MagicMock:
    console = MagicMock()
    console.get.return_value = {"entries": []}
    console.clear.return_value = {}
    return console


@pytest.fixture
def sut(mock_uitree: MagicMock, mock_console: MagicMock) -> MonkeyRunner:
    return MonkeyRunner(mock_uitree, mock_console)


class TestRun:
    def test_performs_count_actions(self, sut: MonkeyRunner) -> None:
        result = sut.run(panel="P", count=5, seed=42, interval=0)
        assert result.total_actions == 5

    def test_clicks_elements(self, sut: MonkeyRunner, mock_uitree: MagicMock) -> None:
        sut.run(panel="P", count=3, seed=42, interval=0)
        assert mock_uitree.click.call_count == 3

    def test_seed_reproducibility(self, sut: MonkeyRunner) -> None:
        r1 = sut.run(panel="P", count=10, seed=42, interval=0)
        r2 = sut.run(panel="P", count=10, seed=42, interval=0)
        refs1 = [a["ref"] for a in r1.actions]
        refs2 = [a["ref"] for a in r2.actions]
        assert refs1 == refs2

    def test_different_seed_different_order(self, sut: MonkeyRunner) -> None:
        r1 = sut.run(panel="P", count=20, seed=1, interval=0)
        r2 = sut.run(panel="P", count=20, seed=2, interval=0)
        refs1 = [a["ref"] for a in r1.actions]
        refs2 = [a["ref"] for a in r2.actions]
        assert refs1 != refs2

    def test_records_actions(self, sut: MonkeyRunner) -> None:
        result = sut.run(panel="P", count=3, seed=42, interval=0)
        assert len(result.actions) == 3
        assert all("ref" in a for a in result.actions)

    def test_default_count_100(self, sut: MonkeyRunner) -> None:
        result = sut.run(panel="P", seed=42, interval=0)
        assert result.total_actions == 100

    def test_returns_seed(self, sut: MonkeyRunner) -> None:
        result = sut.run(panel="P", count=1, seed=42, interval=0)
        assert result.seed == 42

    def test_auto_seed_when_none(self, sut: MonkeyRunner) -> None:
        result = sut.run(panel="P", count=1, interval=0)
        assert result.seed > 0


class TestErrorHandling:
    def test_collects_errors(self, sut: MonkeyRunner, mock_console: MagicMock) -> None:
        mock_console.get.side_effect = [
            {"entries": []},
            {"entries": [{"message": "NullRef"}]},
            {"entries": []},
        ]
        result = sut.run(panel="P", count=3, seed=42, interval=0)
        assert len(result.errors) == 1
        assert result.errors[0]["message"] == "NullRef"

    def test_stop_on_error(self, sut: MonkeyRunner, mock_console: MagicMock) -> None:
        mock_console.get.side_effect = [
            {"entries": [{"message": "Error!"}]},
        ]
        result = sut.run(panel="P", count=10, seed=42, stop_on_error=True, interval=0)
        assert result.total_actions == 1
        assert len(result.errors) == 1

    def test_continues_on_error_by_default(self, sut: MonkeyRunner, mock_console: MagicMock) -> None:
        mock_console.get.side_effect = [
            {"entries": [{"message": "Error!"}]},
            {"entries": []},
            {"entries": []},
        ]
        result = sut.run(panel="P", count=3, seed=42, interval=0)
        assert result.total_actions == 3


class TestEmptyElements:
    def test_stops_when_no_elements(self, sut: MonkeyRunner, mock_uitree: MagicMock) -> None:
        mock_uitree.query.return_value = {"matches": []}
        result = sut.run(panel="P", count=10, seed=42, interval=0)
        assert result.total_actions == 0
