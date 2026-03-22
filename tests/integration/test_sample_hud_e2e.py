"""E2E tests for SampleHUD — Playwright-style UI testing via unity-cli.

Phase 2 of the unity-ui skill workflow.
Tests run against a live Unity Editor with TestProject via Relay.

Usage:
    uv run python -m pytest tests/integration/test_sample_hud_e2e.py -v
"""

from __future__ import annotations

import time

import pytest

from unity_cli.api import ConsoleAPI, EditorAPI, UITreeAPI
from unity_cli.client import RelayConnection

PANEL = "PanelSettings"


@pytest.fixture(scope="module")
def conn() -> RelayConnection:
    conn = RelayConnection(instance="TestProject", timeout=5.0)
    try:
        EditorAPI(conn).get_state()
    except Exception:
        pytest.skip("Relay Server or TestProject not available")
    return conn


@pytest.fixture(scope="module")
def uitree(conn: RelayConnection) -> UITreeAPI:
    return UITreeAPI(conn)


@pytest.fixture(scope="module")
def console(conn: RelayConnection) -> ConsoleAPI:
    return ConsoleAPI(conn)


@pytest.fixture(scope="module")
def editor(conn: RelayConnection) -> EditorAPI:
    return EditorAPI(conn)


@pytest.fixture(autouse=True)
def _play_mode(editor: EditorAPI):
    """Enter Play Mode before each test, exit after."""
    state = editor.get_state()
    if not state.get("isPlaying"):
        editor.play()
        _wait_for(lambda: editor.get_state().get("isPlaying"), timeout=10)
    yield
    # Don't stop between tests — module-scoped play mode is faster


@pytest.fixture(scope="module", autouse=True)
def _stop_after_all(editor: EditorAPI):
    """Stop Play Mode after all tests in this module."""
    yield
    try:
        editor.stop()
    except Exception:
        pass


def _wait_for(predicate, timeout=10, interval=0.5):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return
        time.sleep(interval)
    raise TimeoutError(f"Condition not met within {timeout}s")


# ============================================================
# Functional Tests
# ============================================================


class TestMenuButtons:
    """BtnContinue / BtnNewGame / BtnSettings の Functional テスト。"""

    def test_continue_shows_loading_toast(self, uitree: UITreeAPI) -> None:
        uitree.click(panel=PANEL, name="BtnContinue")
        time.sleep(0.3)

        result = uitree.text(panel=PANEL, name="ToastMessage")
        assert result["text"] == "Loading save data..."

    def test_new_game_resets_profile(self, uitree: UITreeAPI) -> None:
        uitree.click(panel=PANEL, name="BtnNewGame")
        time.sleep(0.3)

        toast = uitree.text(panel=PANEL, name="ToastMessage")
        assert toast["text"] == "Chapter 1 selected"

        profile = uitree.text(panel=PANEL, name="ProfileName")
        assert profile["text"] == "Aria  Lv.1"

    def test_settings_shows_toast(self, uitree: UITreeAPI) -> None:
        uitree.click(panel=PANEL, name="BtnSettings")
        time.sleep(0.3)

        result = uitree.text(panel=PANEL, name="ToastMessage")
        assert result["text"] == "Settings opened"


class TestChapterSelection:
    """Chapter カードの Functional テスト。"""

    def test_chapter1_selects(self, uitree: UITreeAPI) -> None:
        uitree.click(panel=PANEL, name="Chapter1")
        time.sleep(0.3)

        toast = uitree.text(panel=PANEL, name="ToastMessage")
        assert toast["text"] == "Chapter 1 selected"

        info = uitree.inspect(panel=PANEL, name="Chapter1")
        assert "card-selected" in info.get("classes", [])

    def test_chapter3_is_locked(self, uitree: UITreeAPI) -> None:
        uitree.click(panel=PANEL, name="Chapter3")
        time.sleep(0.3)

        toast = uitree.text(panel=PANEL, name="ToastMessage")
        assert toast["text"] == "Chapter III is locked"

        info = uitree.inspect(panel=PANEL, name="Chapter3")
        assert "card-selected" not in info.get("classes", [])


class TestTabSwitching:
    """タブ切り替えの Functional テスト。"""

    def test_quest_tab_activates(self, uitree: UITreeAPI) -> None:
        uitree.click(panel=PANEL, name="TabQuest")
        time.sleep(0.3)

        toast = uitree.text(panel=PANEL, name="ToastMessage")
        assert toast["text"] == "Quest tab"

        quest = uitree.inspect(panel=PANEL, name="TabQuest")
        assert "tab-active" in quest.get("classes", [])

        home = uitree.inspect(panel=PANEL, name="TabHome")
        assert "tab-active" not in home.get("classes", [])

    def test_home_tab_returns(self, uitree: UITreeAPI) -> None:
        uitree.click(panel=PANEL, name="TabQuest")
        time.sleep(0.2)
        uitree.click(panel=PANEL, name="TabHome")
        time.sleep(0.3)

        toast = uitree.text(panel=PANEL, name="ToastMessage")
        assert toast["text"] == "Home tab"

        home = uitree.inspect(panel=PANEL, name="TabHome")
        assert "tab-active" in home.get("classes", [])


# ============================================================
# Smoke Test
# ============================================================


class TestSmoke:
    """全ボタンがクリック可能でエラーを出さないことを確認。"""

    BUTTONS = [
        "BtnContinue",
        "BtnNewGame",
        "BtnSettings",
        "Chapter1",
        "Chapter2",
        "Chapter3",
        "TabHome",
        "TabQuest",
        "TabCodex",
        "TabConfig",
    ]

    def test_all_buttons_clickable_without_errors(self, uitree: UITreeAPI, console: ConsoleAPI) -> None:
        console.clear()

        for btn in self.BUTTONS:
            uitree.click(panel=PANEL, name=btn)
            time.sleep(0.2)

        errors = console.get(types=["error"])
        error_entries = errors.get("entries", [])
        assert error_entries == [], f"Console errors: {error_entries}"


# ============================================================
# Structural Snapshot
# ============================================================


class TestStructuralSnapshot:
    """ツリー構造の変化を検出。"""

    def test_tab_switch_changes_active_class(self, uitree: UITreeAPI) -> None:
        uitree.click(panel=PANEL, name="TabHome")
        time.sleep(0.3)
        before = uitree.dump(panel=PANEL)

        uitree.click(panel=PANEL, name="TabCodex")
        time.sleep(0.3)
        after = uitree.dump(panel=PANEL)

        assert before != after, "Tree should change after tab switch"
