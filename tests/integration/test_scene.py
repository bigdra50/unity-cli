"""Integration tests for SceneAPI commands."""

from __future__ import annotations

import pytest

from unity_cli.api import SceneAPI


class TestActiveScene:
    def test_active_returns_scene_info(self, scene: SceneAPI) -> None:
        actual = scene.get_active()

        assert "name" in actual
        assert "path" in actual
        assert "rootCount" in actual
        assert actual["isLoaded"] is True

    def test_active_scene_has_name(self, scene: SceneAPI) -> None:
        actual = scene.get_active()

        assert isinstance(actual["name"], str)
        assert len(actual["name"]) > 0


class TestHierarchy:
    def test_hierarchy_returns_items(self, scene: SceneAPI) -> None:
        actual = scene.get_hierarchy()

        assert "items" in actual
        assert "totalRootCount" in actual
        assert isinstance(actual["items"], list)

    def test_hierarchy_items_have_required_fields(self, scene: SceneAPI) -> None:
        actual = scene.get_hierarchy(depth=0, page_size=1)
        items = actual["items"]

        assert len(items) > 0
        item = items[0]
        assert "name" in item
        assert "instanceID" in item
        assert "childCount" in item
        assert "activeSelf" in item

    @pytest.mark.parametrize("page_size", [1, 2, 3, 5])
    def test_hierarchy_respects_page_size(self, scene: SceneAPI, page_size: int) -> None:
        actual = scene.get_hierarchy(depth=1, page_size=page_size)

        assert len(actual["items"]) <= page_size

    def test_hierarchy_pagination_covers_all_roots(self, scene: SceneAPI) -> None:
        total = scene.get_active()["rootCount"]
        cursor = 0
        collected = 0
        iterations = 0

        while cursor != -1 and iterations < 100:
            result = scene.get_hierarchy(depth=0, page_size=2, cursor=cursor)
            collected += len(result["items"])
            cursor = result["nextCursor"] if result["hasMore"] else -1
            iterations += 1

        assert collected == total

    def test_hierarchy_depth_zero_returns_roots_only(self, scene: SceneAPI) -> None:
        actual = scene.get_hierarchy(depth=0, page_size=100)

        for item in actual["items"]:
            assert item["depth"] == 0
