"""Integration tests for UITreeAPI commands."""

from __future__ import annotations

import pytest

from unity_cli.api import UITreeAPI

pytestmark = pytest.mark.integration


class TestDump:
    def test_dump_lists_panels(self, uitree: UITreeAPI) -> None:
        response = uitree.dump()

        assert "panels" in response
        assert isinstance(response["panels"], list)
        assert len(response["panels"]) > 0

    def test_dump_panel_returns_tree(self, uitree: UITreeAPI) -> None:
        panels = uitree.dump()["panels"]
        assert len(panels) > 0
        panel_name = panels[0]["name"]

        response = uitree.dump(panel=panel_name, depth=1)

        assert "tree" in response
