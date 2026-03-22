"""E2E tests for SampleHUD — pytest + unity-cli API."""

from __future__ import annotations

import re
import time

import pytest

from unity_cli.api import ConsoleAPI, EditorAPI, UITreeAPI

PANEL = "UIDocument SamplePanelSettings (SampleHUD)"


# conn / uitree / console / editor fixtures are provided by conftest.py (session scope)


@pytest.fixture(autouse=True)
def _play_mode(editor: EditorAPI) -> None:
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
def _stop_after_all(editor: EditorAPI):
    """Stop Play Mode after all tests in this module."""
    yield
    try:
        editor.stop()
    except Exception:
        pass


# --- Functional tests ---


class TestMenuButtons:
    def test_continue_shows_toast(self, uitree: UITreeAPI) -> None:
        uitree.click(panel=PANEL, name="BtnContinue")
        time.sleep(0.3)
        result = uitree.text(panel=PANEL, name="ToastMessage")
        assert result["text"] == "Loading save data..."

    def test_new_game_shows_toast(self, uitree: UITreeAPI) -> None:
        uitree.click(panel=PANEL, name="BtnNewGame")
        time.sleep(0.3)
        result = uitree.text(panel=PANEL, name="ToastMessage")
        assert result["text"] == "Chapter 1 selected"

    def test_settings_shows_toast(self, uitree: UITreeAPI) -> None:
        uitree.click(panel=PANEL, name="BtnSettings")
        time.sleep(0.3)
        result = uitree.text(panel=PANEL, name="ToastMessage")
        assert result["text"] == "Settings opened"


class TestLabels:
    def test_profile_name_displayed(self, uitree: UITreeAPI) -> None:
        # ProfileName is dynamic (level changes each play session); verify format only
        result = uitree.text(panel=PANEL, name="ProfileName")
        assert re.match(r"Aria\s+Lv\.\d+", result["text"]), f"ProfileName format mismatch: {result['text']!r}"

    def test_progress_label_displayed(self, uitree: UITreeAPI) -> None:
        result = uitree.text(panel=PANEL, name="ProgressLabel")
        assert result["text"] == "Story Progress"

    def test_progress_percent_displayed(self, uitree: UITreeAPI) -> None:
        # ProgressPercent is dynamic; verify it is a percentage string
        result = uitree.text(panel=PANEL, name="ProgressPercent")
        assert re.match(r"\d+%", result["text"]), f"ProgressPercent format mismatch: {result['text']!r}"

    def test_chapter1_status_complete(self, uitree: UITreeAPI) -> None:
        result = uitree.text(panel=PANEL, name="Chapter1Status")
        assert result["text"] == "Complete"

    def test_chapter2_status_in_progress(self, uitree: UITreeAPI) -> None:
        result = uitree.text(panel=PANEL, name="Chapter2Status")
        assert result["text"] == "In Progress"

    def test_chapter3_status_locked(self, uitree: UITreeAPI) -> None:
        result = uitree.text(panel=PANEL, name="Chapter3Status")
        assert result["text"] == "Locked"


# --- Smoke tests ---


class TestSmoke:
    BUTTONS = ["BtnContinue", "BtnNewGame", "BtnSettings"]
    TABS = ["TabHome", "TabQuest", "TabCodex", "TabConfig"]

    def test_all_buttons_clickable_without_errors(self, uitree: UITreeAPI, console: ConsoleAPI) -> None:
        console.clear()
        for btn in self.BUTTONS:
            uitree.click(panel=PANEL, name=btn)
            time.sleep(0.2)
        errors = console.get(types=["error"])
        assert errors.get("entries", []) == []

    def test_all_tabs_clickable_without_errors(self, uitree: UITreeAPI, console: ConsoleAPI) -> None:
        console.clear()
        for tab in self.TABS:
            uitree.click(panel=PANEL, name=tab)
            time.sleep(0.2)
        errors = console.get(types=["error"])
        assert errors.get("entries", []) == []


# --- Structural Snapshot tests ---


class TestStructure:
    def test_panel_has_expected_element_count(self, uitree: UITreeAPI) -> None:
        result = uitree.dump(panel=PANEL)
        assert result.get("elementCount", 0) >= 60

    def test_tab_switch_changes_tree(self, uitree: UITreeAPI) -> None:
        uitree.click(panel=PANEL, name="TabHome")
        time.sleep(0.3)
        before = uitree.dump(panel=PANEL)

        uitree.click(panel=PANEL, name="TabQuest")
        time.sleep(0.3)
        after = uitree.dump(panel=PANEL)

        assert before != after

    def test_tree_contains_required_sections(self, uitree: UITreeAPI) -> None:
        result = uitree.dump(panel=PANEL)
        tree_str = str(result)
        for section in ("StatusBar", "TitleCard", "Chapters", "Menu", "TabBar"):
            assert section in tree_str, f"Expected section '{section}' not found in tree"
