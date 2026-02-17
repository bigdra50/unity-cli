"""Integration tests for SceneAPI commands."""

from __future__ import annotations

from typing import Any

import pytest

from unity_cli.api import SceneAPI

pytestmark = pytest.mark.integration


def _collect_all_roots(
    scene: SceneAPI,
    page_size: int,
    *,
    max_pages: int = 50,
) -> list[dict[str, Any]]:
    """Collect all root items via pagination."""
    items: list[dict[str, Any]] = []
    cursor = 0
    prev_cursor = -1

    for _ in range(max_pages):
        result = scene.get_hierarchy(depth=0, page_size=page_size, cursor=cursor)
        items.extend(result["items"])
        if not result["hasMore"]:
            return items
        next_cursor = result["nextCursor"]
        if next_cursor == prev_cursor:
            pytest.fail(f"Pagination stalled at cursor={cursor}")
        prev_cursor = cursor
        cursor = next_cursor

    pytest.fail(f"Pagination did not complete within {max_pages} pages")
    return items  # unreachable, for type checker


class TestActiveScene:
    def test_active_returns_scene_info(self, scene: SceneAPI) -> None:
        response = scene.get_active()

        assert "name" in response
        assert "path" in response
        assert "rootCount" in response
        assert response["isLoaded"] is True

    def test_active_scene_has_name(self, scene: SceneAPI) -> None:
        response = scene.get_active()

        assert isinstance(response["name"], str)
        assert len(response["name"]) > 0


class TestHierarchy:
    def test_hierarchy_returns_items(self, scene: SceneAPI) -> None:
        response = scene.get_hierarchy()

        assert "items" in response
        assert "totalRootCount" in response
        assert isinstance(response["items"], list)

    def test_hierarchy_items_have_required_fields(self, scene: SceneAPI) -> None:
        response = scene.get_hierarchy(depth=0, page_size=1)
        items = response["items"]

        assert len(items) > 0
        item = items[0]
        assert "name" in item
        assert "instanceID" in item
        assert "childCount" in item
        assert "activeSelf" in item

    @pytest.mark.parametrize("page_size", [1, 2, 3, 5])
    def test_hierarchy_respects_page_size(self, scene: SceneAPI, page_size: int) -> None:
        response = scene.get_hierarchy(depth=1, page_size=page_size)

        assert len(response["items"]) <= page_size

    def test_hierarchy_pagination_covers_all_roots(self, scene: SceneAPI) -> None:
        total = scene.get_active()["rootCount"]
        items = _collect_all_roots(scene, page_size=2)

        assert len(items) == total

    def test_hierarchy_depth_zero_returns_roots_only(self, scene: SceneAPI) -> None:
        response = scene.get_hierarchy(depth=0, page_size=100)

        for item in response["items"]:
            assert item["depth"] == 0
