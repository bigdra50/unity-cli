"""Integration tests for GameObjectAPI commands."""

from __future__ import annotations

import pytest

from unity_cli.api import GameObjectAPI


class TestFind:
    def test_find_returns_list(self, gameobject: GameObjectAPI) -> None:
        actual = gameobject.find(name="Main Camera")

        assert "objects" in actual
        assert isinstance(actual["objects"], list)

    def test_find_existing_object(self, gameobject: GameObjectAPI) -> None:
        actual = gameobject.find(name="Main Camera")

        names = [go["name"] for go in actual["objects"]]
        assert "Main Camera" in names

    def test_find_nonexistent_returns_empty(self, gameobject: GameObjectAPI) -> None:
        actual = gameobject.find(name="NonExistentObject_12345")

        assert actual["found"] == 0
        assert len(actual["objects"]) == 0


class TestCreateAndDelete:
    def test_create_and_delete_lifecycle(self, gameobject: GameObjectAPI) -> None:
        name = "_IntegrationTest_Temp"

        # Cleanup leftover from previous failed runs
        for _ in range(5):
            if gameobject.find(name=name)["found"] == 0:
                break
            gameobject.delete(name=name)

        create_result = gameobject.create(name=name)
        assert create_result["gameObject"]["name"] == name

        find_result = gameobject.find(name=name)
        assert find_result["found"] > 0

        gameobject.delete(name=name)

        find_after = gameobject.find(name=name)
        assert find_after["found"] == 0


class TestModify:
    def test_modify_position(self, gameobject: GameObjectAPI) -> None:
        name = "_IntegrationTest_Modify"

        try:
            gameobject.create(name=name)
            gameobject.modify(name=name, position=[1.0, 2.0, 3.0])
            result = gameobject.find(name=name)
            go = result["objects"][0]

            assert go["position"][0] == pytest.approx(1.0, abs=0.01)
            assert go["position"][1] == pytest.approx(2.0, abs=0.01)
            assert go["position"][2] == pytest.approx(3.0, abs=0.01)
        finally:
            gameobject.delete(name=name)

    def test_set_active_toggle(self, gameobject: GameObjectAPI) -> None:
        name = "_IntegrationTest_Active"

        try:
            gameobject.create(name=name)

            gameobject.set_active(name=name, active=False)
            result = gameobject.find(name=name)
            assert result["objects"][0]["active"] is False

            gameobject.set_active(name=name, active=True)
            result = gameobject.find(name=name)
            assert result["objects"][0]["active"] is True
        finally:
            gameobject.delete(name=name)
