"""Integration tests for UITreeAPI commands."""

from __future__ import annotations

from unity_cli.api import UITreeAPI


class TestDump:
    def test_dump_lists_panels(self, uitree: UITreeAPI) -> None:
        actual = uitree.dump()

        assert "panels" in actual
        assert isinstance(actual["panels"], list)
        assert len(actual["panels"]) > 0

    def test_dump_panel_returns_tree(self, uitree: UITreeAPI) -> None:
        panels = uitree.dump()["panels"]
        assert len(panels) > 0
        panel_name = panels[0]["name"]

        actual = uitree.dump(panel=panel_name, depth=1)

        assert "tree" in actual
