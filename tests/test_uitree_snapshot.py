"""Tests for unity_cli/api/uitree_snapshot.py"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from unity_cli.api.uitree_snapshot import SnapshotStore

SAMPLE_TREE: dict[str, Any] = {
    "tree": {
        "ref": "ref_1",
        "name": "Root",
        "type": "VisualElement",
        "classes": ["root"],
        "children": [
            {
                "ref": "ref_2",
                "name": "BtnStart",
                "type": "VisualElement",
                "classes": ["action-btn"],
                "children": [],
            },
            {
                "ref": "ref_3",
                "name": "TabHome",
                "type": "VisualElement",
                "classes": ["tab", "tab-active"],
                "children": [],
            },
        ],
    }
}


@pytest.fixture
def store(tmp_path: Path) -> SnapshotStore:
    return SnapshotStore(snapshot_dir=tmp_path / "snapshots")


class TestSaveLoad:
    def test_save_creates_file(self, store: SnapshotStore) -> None:
        path = store.save("baseline", SAMPLE_TREE)
        assert path.exists()

    def test_load_returns_saved_data(self, store: SnapshotStore) -> None:
        store.save("baseline", SAMPLE_TREE)
        result = store.load("baseline")
        assert result == SAMPLE_TREE

    def test_load_returns_none_when_missing(self, store: SnapshotStore) -> None:
        assert store.load("nonexistent") is None

    def test_invalid_name_raises(self, store: SnapshotStore) -> None:
        with pytest.raises(ValueError, match="Invalid snapshot name"):
            store.save("../escape", SAMPLE_TREE)


class TestDiff:
    def test_no_changes(self, store: SnapshotStore) -> None:
        store.save("baseline", SAMPLE_TREE)
        result = store.diff("baseline", SAMPLE_TREE)
        assert result["added"] == []
        assert result["removed"] == []
        assert result["changed"] == []

    def test_detects_class_change(self, store: SnapshotStore) -> None:
        store.save("baseline", SAMPLE_TREE)
        modified = {
            "tree": {
                **SAMPLE_TREE["tree"],
                "children": [
                    SAMPLE_TREE["tree"]["children"][0],
                    {
                        **SAMPLE_TREE["tree"]["children"][1],
                        "classes": ["tab"],  # tab-active removed
                    },
                ],
            }
        }
        result = store.diff("baseline", modified)
        assert len(result["changed"]) == 1
        assert result["changed"][0]["name"] == "TabHome"

    def test_detects_added_element(self, store: SnapshotStore) -> None:
        store.save("baseline", SAMPLE_TREE)
        modified = {
            "tree": {
                **SAMPLE_TREE["tree"],
                "children": [
                    *SAMPLE_TREE["tree"]["children"],
                    {"ref": "ref_4", "name": "NewBtn", "type": "Button", "classes": [], "children": []},
                ],
            }
        }
        result = store.diff("baseline", modified)
        assert len(result["added"]) == 1
        assert result["added"][0]["name"] == "NewBtn"

    def test_detects_removed_element(self, store: SnapshotStore) -> None:
        store.save("baseline", SAMPLE_TREE)
        modified = {
            "tree": {
                **SAMPLE_TREE["tree"],
                "children": [SAMPLE_TREE["tree"]["children"][0]],
            }
        }
        result = store.diff("baseline", modified)
        assert len(result["removed"]) == 1
        assert result["removed"][0]["name"] == "TabHome"

    def test_missing_baseline_raises(self, store: SnapshotStore) -> None:
        with pytest.raises(FileNotFoundError):
            store.diff("nonexistent", SAMPLE_TREE)


class TestListDelete:
    def test_list_empty(self, store: SnapshotStore) -> None:
        assert store.list_names() == []

    def test_list_returns_names(self, store: SnapshotStore) -> None:
        store.save("alpha", SAMPLE_TREE)
        store.save("beta", SAMPLE_TREE)
        assert store.list_names() == ["alpha", "beta"]

    def test_delete_existing(self, store: SnapshotStore) -> None:
        store.save("baseline", SAMPLE_TREE)
        assert store.delete("baseline") is True
        assert store.load("baseline") is None

    def test_delete_nonexistent(self, store: SnapshotStore) -> None:
        assert store.delete("nonexistent") is False
