"""E2E tests for SampleHUD monkey + snapshot — pytest + unity-cli API."""

from __future__ import annotations

import time
from collections.abc import Iterator

import pytest

from unity_cli.api import ConsoleAPI, EditorAPI, UITreeAPI
from unity_cli.api.uitree_monkey import MonkeyRunner
from unity_cli.api.uitree_snapshot import SnapshotStore

PANEL = "UIDocument SamplePanelSettings (SampleHUD)"

# conn / uitree / console / editor fixtures are provided by conftest.py (session scope)


@pytest.fixture(autouse=True)
def _play_mode(editor: EditorAPI) -> Iterator[None]:
    """Ensure Play Mode is active before each test."""
    state = editor.get_state()
    if not state.get("isPlaying"):
        editor.play()
        deadline = time.time() + 10
        while time.time() < deadline:
            if editor.get_state().get("isPlaying"):
                break
            time.sleep(0.5)
    yield


@pytest.fixture(scope="module", autouse=True)
def _stop_after_all(editor: EditorAPI) -> Iterator[None]:
    """Stop Play Mode after all tests in this module."""
    yield
    try:
        editor.stop()
    except Exception:
        pass


# --- Monkey tests ---


class TestMonkey:
    def test_random_clicks_no_errors(self, uitree: UITreeAPI, console: ConsoleAPI) -> None:
        runner = MonkeyRunner(uitree, console)
        result = runner.run(panel=PANEL, class_filter="action-btn", count=20, seed=42, interval=0.2)
        assert result.errors == [], f"Monkey errors: {result.errors}"

    def test_random_clicks_actions_count(self, uitree: UITreeAPI, console: ConsoleAPI) -> None:
        runner = MonkeyRunner(uitree, console)
        result = runner.run(panel=PANEL, class_filter="action-btn", count=10, seed=123, interval=0.1)
        assert result.total_actions == 10
        assert result.errors == [], f"Monkey errors: {result.errors}"

    def test_seed_reproducibility(self, uitree: UITreeAPI, console: ConsoleAPI) -> None:
        """同じ seed は同じ操作順序を再現する。"""
        runner = MonkeyRunner(uitree, console)
        result1 = runner.run(panel=PANEL, class_filter="action-btn", count=5, seed=999, interval=0.1)
        result2 = runner.run(panel=PANEL, class_filter="action-btn", count=5, seed=999, interval=0.1)
        refs1 = [a["ref"] for a in result1.actions]
        refs2 = [a["ref"] for a in result2.actions]
        assert refs1 == refs2, "Same seed should produce the same action sequence"


# --- Snapshot tests ---


class TestSnapshot:
    def test_save_and_diff_no_changes(self, uitree: UITreeAPI, tmp_path: pytest.TempPathFactory) -> None:
        """変更なしなら diff が空。"""
        store = SnapshotStore(snapshot_dir=tmp_path / "snapshots")
        # monkey テストの副作用 (Toast 表示) が消えるのを待ってから baseline を取る
        uitree.click(panel=PANEL, name="TabHome")
        time.sleep(1.0)
        data = uitree.dump(panel=PANEL, format="json")
        store.save("baseline", data)
        current = uitree.dump(panel=PANEL, format="json")
        result = store.diff("baseline", current)
        assert result["added"] == []
        assert result["removed"] == []
        assert result["changed"] == []

    def test_tab_switch_detected_as_change(self, uitree: UITreeAPI, tmp_path: pytest.TempPathFactory) -> None:
        """タブ切り替え後の class 変化を diff が検出する。"""
        store = SnapshotStore(snapshot_dir=tmp_path / "snapshots")

        # TabHome がアクティブな状態で baseline を保存
        uitree.click(panel=PANEL, name="TabHome")
        time.sleep(0.3)
        baseline = uitree.dump(panel=PANEL, format="json")
        store.save("tab_baseline", baseline)

        # TabQuest に切り替えて差分を取る
        uitree.click(panel=PANEL, name="TabQuest")
        time.sleep(0.3)
        current = uitree.dump(panel=PANEL, format="json")

        result = store.diff("tab_baseline", current)
        # tab-active クラスの付け替えが changed に現れる
        assert result["changed"] != [], "Tab switch should produce class changes"

    def test_snapshot_not_found_raises(self, uitree: UITreeAPI, tmp_path: pytest.TempPathFactory) -> None:
        """存在しない snapshot を diff すると FileNotFoundError。"""
        store = SnapshotStore(snapshot_dir=tmp_path / "snapshots")
        current = uitree.dump(panel=PANEL, format="json")
        with pytest.raises(FileNotFoundError):
            store.diff("nonexistent", current)
