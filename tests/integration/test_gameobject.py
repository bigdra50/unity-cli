"""Integration tests for GameObjectAPI commands."""

from __future__ import annotations

import uuid

import pytest

from unity_cli.api import GameObjectAPI

pytestmark = pytest.mark.integration


class TestFind:
    def test_find_returns_list(self, gameobject: GameObjectAPI) -> None:
        response = gameobject.find(name="Main Camera")

        assert "objects" in response
        assert isinstance(response["objects"], list)

    def test_find_existing_object(self, gameobject: GameObjectAPI) -> None:
        response = gameobject.find(name="Main Camera")

        assert any(go["name"] == "Main Camera" for go in response["objects"])

    def test_find_nonexistent_returns_empty(self, gameobject: GameObjectAPI) -> None:
        response = gameobject.find(name="NonExistentObject_12345")

        assert response["found"] == 0
        assert len(response["objects"]) == 0


class TestCreateAndDelete:
    def test_create_and_delete_lifecycle(self, gameobject: GameObjectAPI) -> None:
        name = f"_Test_{uuid.uuid4().hex[:8]}"
        instance_id = None

        try:
            result = gameobject.create(name=name)
            instance_id = result["gameObject"]["instanceID"]
            assert result["gameObject"]["name"] == name
            assert gameobject.find(name=name)["found"] > 0

            gameobject.delete(instance_id=instance_id)
            instance_id = None

            assert gameobject.find(name=name)["found"] == 0
        finally:
            if instance_id is not None:
                gameobject.delete(instance_id=instance_id)


class TestModify:
    def test_modify_position(self, gameobject: GameObjectAPI, temp_gameobject) -> None:
        name, _ = temp_gameobject()

        gameobject.modify(name=name, position=[1.0, 2.0, 3.0])
        response = gameobject.find(name=name)
        pos = response["objects"][0]["position"]

        assert pos[0] == pytest.approx(1.0, abs=0.01)
        assert pos[1] == pytest.approx(2.0, abs=0.01)
        assert pos[2] == pytest.approx(3.0, abs=0.01)

    def test_set_active_toggle(self, gameobject: GameObjectAPI, temp_gameobject) -> None:
        name, _ = temp_gameobject()

        gameobject.set_active(name=name, active=False)
        response = gameobject.find(name=name)
        assert response["objects"][0]["active"] is False

        gameobject.set_active(name=name, active=True)
        response = gameobject.find(name=name)
        assert response["objects"][0]["active"] is True
