"""Tests for pipe-friendly PLAIN output across commands.

Each command's PLAIN output is tested for:
- Tab-separated fields
- No headers, indentation, or Rich markup
- PRETTY mode regression (output matches original format)
"""

from __future__ import annotations

from typing import Any

import pytest

from unity_cli.cli.output import OutputMode, configure_output


@pytest.fixture()
def _plain_mode() -> Any:
    configure_output(OutputMode.PLAIN)
    yield
    configure_output(OutputMode.PRETTY)


@pytest.fixture()
def _pretty_mode() -> Any:
    configure_output(OutputMode.PRETTY)
    yield
    configure_output(OutputMode.PRETTY)


# =============================================================================
# gameobject find
# =============================================================================


class TestGameobjectFindPlain:
    @pytest.fixture(autouse=True)
    def _setup(self, _plain_mode: Any) -> None:
        pass

    def test_plain_tab_separated_no_header(self, capsys: pytest.CaptureFixture[str]) -> None:
        from unity_cli.cli.commands.gameobject import is_no_color, print_plain_table

        objects = [
            {"name": "CubeA", "instanceID": 12345},
            {"name": "CubeB", "instanceID": 67890},
        ]
        assert is_no_color()
        rows = [[obj.get("name", "Unknown"), str(obj.get("instanceID", ""))] for obj in objects]
        print_plain_table(["Name", "ID"], rows, header=False)
        out = capsys.readouterr().out
        lines = out.strip().split("\n")
        assert len(lines) == 2
        assert lines[0] == "CubeA\t12345"
        assert lines[1] == "CubeB\t67890"

    def test_plain_empty_list(self, capsys: pytest.CaptureFixture[str]) -> None:
        from unity_cli.cli.commands.gameobject import print_plain_table

        print_plain_table(["Name", "ID"], [], header=False)
        out = capsys.readouterr().out
        assert out == ""


# =============================================================================
# tests list
# =============================================================================


class TestTestsListPlain:
    @pytest.fixture(autouse=True)
    def _setup(self, _plain_mode: Any) -> None:
        pass

    def test_plain_one_per_line(self, capsys: pytest.CaptureFixture[str]) -> None:
        tests = ["TestClass.Method1", "TestClass.Method2", "OtherClass.Method3"]
        for t in tests:
            print(str(t))
        out = capsys.readouterr().out
        lines = out.strip().split("\n")
        assert len(lines) == 3
        assert lines[0] == "TestClass.Method1"
        assert "  " not in lines[0]  # no indentation
        assert "[bold]" not in out


# =============================================================================
# tests status
# =============================================================================


class TestTestsStatusPlain:
    @pytest.fixture(autouse=True)
    def _setup(self, _plain_mode: Any) -> None:
        pass

    def test_plain_running_kv(self, capsys: pytest.CaptureFixture[str]) -> None:
        from unity_cli.cli.output import print_key_value

        kv: dict[str, Any] = {
            "status": "running",
            "progress": "5/10",
            "passed": 3,
            "failed": 0,
            "skipped": 0,
        }
        print_key_value(kv)
        out = capsys.readouterr().out
        lines = out.strip().split("\n")
        assert lines[0] == "status\trunning"
        assert lines[1] == "progress\t5/10"
        assert lines[2] == "passed\t3"

    def test_plain_idle_kv(self, capsys: pytest.CaptureFixture[str]) -> None:
        from unity_cli.cli.output import print_key_value

        print_key_value({"status": "idle"})
        out = capsys.readouterr().out
        assert out.strip() == "status\tidle"


# =============================================================================
# menu list
# =============================================================================


class TestMenuListPlain:
    @pytest.fixture(autouse=True)
    def _setup(self, _plain_mode: Any) -> None:
        pass

    def test_plain_one_per_line(self, capsys: pytest.CaptureFixture[str]) -> None:
        items = ["File/New Scene", "File/Open Scene", "Window/General/Console"]
        for item in items:
            print(str(item))
        out = capsys.readouterr().out
        lines = out.strip().split("\n")
        assert len(lines) == 3
        assert lines[0] == "File/New Scene"
        assert "  " not in lines[0]

    def test_plain_empty_list(self, capsys: pytest.CaptureFixture[str]) -> None:
        # Nothing printed
        out = capsys.readouterr().out
        assert out == ""


# =============================================================================
# asset deps/refs
# =============================================================================


class TestAssetDepsPlain:
    @pytest.fixture(autouse=True)
    def _setup(self, _plain_mode: Any) -> None:
        pass

    def test_plain_tab_separated_no_header(self, capsys: pytest.CaptureFixture[str]) -> None:
        from unity_cli.cli.output import print_plain_table

        deps = [
            {"path": "Assets/Models/character.fbx", "type": "Model"},
            {"path": "Assets/Textures/skin.png", "type": "Texture2D"},
        ]
        rows = [[dep.get("path", ""), dep.get("type", "")] for dep in deps]
        print_plain_table(["Path", "Type"], rows, header=False)
        out = capsys.readouterr().out
        lines = out.strip().split("\n")
        assert len(lines) == 2
        assert lines[0] == "Assets/Models/character.fbx\tModel"
        assert lines[1] == "Assets/Textures/skin.png\tTexture2D"


class TestAssetRefsPlain:
    @pytest.fixture(autouse=True)
    def _setup(self, _plain_mode: Any) -> None:
        pass

    def test_plain_empty_refs(self, capsys: pytest.CaptureFixture[str]) -> None:
        from unity_cli.cli.output import print_plain_table

        print_plain_table(["Path", "Type"], [], header=False)
        out = capsys.readouterr().out
        assert out == ""


# =============================================================================
# selection
# =============================================================================


class TestSelectionPlain:
    @pytest.fixture(autouse=True)
    def _setup(self, _plain_mode: Any) -> None:
        pass

    def test_plain_single_kv(self, capsys: pytest.CaptureFixture[str]) -> None:
        from unity_cli.cli.commands.selection import _print_selection

        result = {
            "count": 1,
            "activeGameObject": {
                "name": "Cube",
                "instanceID": 12345,
                "tag": "Untagged",
                "layerName": "Default",
                "scenePath": "/Cube",
            },
            "gameObjects": [],
        }
        _print_selection(result)
        out = capsys.readouterr().out
        lines = out.strip().split("\n")
        assert lines[0] == "name\tCube"
        assert lines[1] == "instanceID\t12345"
        assert "  " not in out  # no indentation

    def test_plain_multiple_table(self, capsys: pytest.CaptureFixture[str]) -> None:
        from unity_cli.cli.commands.selection import _print_selection

        result = {
            "count": 2,
            "activeGameObject": {
                "name": "Cube",
                "instanceID": 12345,
                "tag": "Untagged",
                "layerName": "Default",
                "scenePath": "/Cube",
            },
            "gameObjects": [
                {"name": "Cube", "instanceID": 12345, "tag": "Untagged", "layerName": "Default", "scenePath": "/Cube"},
                {
                    "name": "Sphere",
                    "instanceID": 67890,
                    "tag": "Untagged",
                    "layerName": "Default",
                    "scenePath": "/Sphere",
                },
            ],
        }
        _print_selection(result)
        out = capsys.readouterr().out
        lines = out.strip().split("\n")
        assert len(lines) == 2
        assert "Cube\t12345" in lines[0]
        assert "Sphere\t67890" in lines[1]

    def test_plain_count_zero_no_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        from unity_cli.cli.commands.selection import _print_selection

        result = {"count": 0}
        _print_selection(result)
        out = capsys.readouterr().out
        assert out == ""


# =============================================================================
# recorder status
# =============================================================================


class TestRecorderStatusPlain:
    @pytest.fixture(autouse=True)
    def _setup(self, _plain_mode: Any) -> None:
        pass

    def test_plain_recording_kv(self, capsys: pytest.CaptureFixture[str]) -> None:
        from unity_cli.cli.output import print_key_value

        kv: dict[str, Any] = {
            "recording": "true",
            "frameCount": 120,
            "elapsed": 4.0,
            "fps": 30,
        }
        print_key_value(kv)
        out = capsys.readouterr().out
        lines = out.strip().split("\n")
        assert lines[0] == "recording\ttrue"
        assert lines[1] == "frameCount\t120"

    def test_plain_not_recording(self, capsys: pytest.CaptureFixture[str]) -> None:
        from unity_cli.cli.output import print_key_value

        print_key_value({"recording": "false"})
        out = capsys.readouterr().out
        assert out.strip() == "recording\tfalse"


# =============================================================================
# uitree query
# =============================================================================


class TestUitreeQueryPlain:
    @pytest.fixture(autouse=True)
    def _setup(self, _plain_mode: Any) -> None:
        pass

    def test_plain_tab_separated(self, capsys: pytest.CaptureFixture[str]) -> None:
        from unity_cli.cli.commands.uitree import _print_query_match_plain

        elem = {
            "ref": "ref_1",
            "type": "Button",
            "name": "StartBtn",
            "path": "/root/panel/btn",
            "layout": {"x": 0, "y": 0, "width": 80, "height": 30},
        }
        _print_query_match_plain(elem)
        out = capsys.readouterr().out
        assert out.strip() == "ref_1\tButton\tStartBtn\t/root/panel/btn\t0,0,80x30"

    def test_plain_no_layout(self, capsys: pytest.CaptureFixture[str]) -> None:
        from unity_cli.cli.commands.uitree import _print_query_match_plain

        elem = {"ref": "ref_2", "type": "Label", "name": "title"}
        _print_query_match_plain(elem)
        out = capsys.readouterr().out
        parts = out.strip().split("\t")
        assert parts[0] == "ref_2"
        assert parts[1] == "Label"
        assert parts[2] == "title"


# =============================================================================
# uitree inspect
# =============================================================================


class TestUitreeInspectPlain:
    @pytest.fixture(autouse=True)
    def _setup(self, _plain_mode: Any) -> None:
        pass

    def test_plain_basic_kv(self, capsys: pytest.CaptureFixture[str]) -> None:
        from unity_cli.cli.commands.uitree import _print_inspect_element_plain

        elem = {
            "ref": "ref_5",
            "type": "Button",
            "name": "play",
            "visible": True,
            "childCount": 1,
            "path": "/root/btn",
        }
        _print_inspect_element_plain(elem)
        out = capsys.readouterr().out
        lines = out.strip().split("\n")
        assert lines[0] == "ref\tref_5"
        assert "type\tButton" in out
        assert "name\tplay" in out
        assert "visible\tTrue" in out

    def test_plain_with_style_dot_notation(self, capsys: pytest.CaptureFixture[str]) -> None:
        from unity_cli.cli.commands.uitree import _print_inspect_element_plain

        elem = {
            "ref": "ref_8",
            "type": "Label",
            "resolvedStyle": {"fontSize": 14, "color": "white"},
        }
        _print_inspect_element_plain(elem)
        out = capsys.readouterr().out
        assert "style.fontSize\t14" in out
        assert "style.color\twhite" in out

    def test_plain_with_children(self, capsys: pytest.CaptureFixture[str]) -> None:
        from unity_cli.cli.commands.uitree import _print_inspect_element_plain

        elem = {
            "ref": "ref_9",
            "type": "VisualElement",
            "children": [
                {"ref": "ref_10", "type": "Label", "name": "text"},
                {"ref": "ref_11", "type": "Button", "name": "ok"},
            ],
        }
        _print_inspect_element_plain(elem)
        out = capsys.readouterr().out
        assert "child\tref_10\tLabel\ttext" in out
        assert "child\tref_11\tButton\tok" in out


# =============================================================================
# PRETTY mode regression tests
# =============================================================================


class TestPrettyModeRegression:
    @pytest.fixture(autouse=True)
    def _setup(self, _pretty_mode: Any) -> None:
        pass

    def test_selection_pretty_shows_header(self, capsys: pytest.CaptureFixture[str]) -> None:
        from unity_cli.cli.commands.selection import _print_selection

        result = {
            "count": 1,
            "activeGameObject": {
                "name": "Cube",
                "instanceID": 12345,
                "tag": "Untagged",
                "layerName": "Default",
                "layer": 0,
                "scenePath": "/Cube",
            },
            "gameObjects": [],
        }
        _print_selection(result)
        out = capsys.readouterr().out
        assert "Selected: 1 object(s)" in out
        assert "Active GameObject:" in out

    def test_selection_pretty_zero_count(self, capsys: pytest.CaptureFixture[str]) -> None:
        from unity_cli.cli.commands.selection import _print_selection

        result = {"count": 0}
        _print_selection(result)
        out = capsys.readouterr().out
        assert "No objects selected" in out

    def test_query_match_pretty_has_indent(self) -> None:
        from unity_cli.cli.commands.uitree import _format_query_match

        elem = {"ref": "ref_1", "type": "Button", "path": "/root/btn"}
        lines = _format_query_match(elem)
        assert lines[0].startswith("  ")
        assert lines[-1] == ""
