"""Tests for uitree format helpers (pure functions in commands/uitree.py)."""

from __future__ import annotations

from unity_cli.cli.commands.uitree import (
    _format_element_children,
    _format_element_detail,
    _format_element_header,
    _format_element_style,
    _format_inspect_element,
    _format_query_match,
)


class TestFormatElementHeader:
    def test_ref_and_type(self) -> None:
        elem = {"ref": "ref_1", "type": "Button"}
        assert _format_element_header(elem) == ["ref_1 Button"]

    def test_with_name(self) -> None:
        elem = {"ref": "ref_2", "type": "Label", "name": "title"}
        lines = _format_element_header(elem)
        assert lines[0] == 'ref_2 Label "title"'

    def test_with_classes(self) -> None:
        elem = {"ref": "ref_3", "type": "Button", "classes": ["primary", "large"]}
        lines = _format_element_header(elem)
        assert lines == ["ref_3 Button", "  classes: .primary .large"]

    def test_no_ref(self) -> None:
        elem = {"type": "VisualElement"}
        assert _format_element_header(elem) == ["VisualElement"]

    def test_empty_name_excluded(self) -> None:
        elem = {"ref": "ref_4", "type": "Toggle", "name": ""}
        assert _format_element_header(elem) == ["ref_4 Toggle"]

    def test_empty_classes_excluded(self) -> None:
        elem = {"ref": "ref_5", "type": "Slider", "classes": []}
        assert len(_format_element_header(elem)) == 1

    # --- 異常データ ---

    def test_classes_none_ignored(self) -> None:
        elem = {"ref": "ref_6", "type": "Button", "classes": None}
        assert _format_element_header(elem) == ["ref_6 Button"]

    def test_classes_string_ignored(self) -> None:
        elem = {"ref": "ref_7", "type": "Button", "classes": "primary"}
        assert _format_element_header(elem) == ["ref_7 Button"]


class TestFormatElementDetail:
    def test_visible_and_focusable(self) -> None:
        elem = {"visible": True, "focusable": False}
        lines = _format_element_detail(elem)
        assert "  visible: True" in lines
        assert "  focusable: False" in lines

    def test_enabled_with_hierarchy(self) -> None:
        elem = {"enabledSelf": True, "enabledInHierarchy": False}
        lines = _format_element_detail(elem)
        assert "  enabled: True (hierarchy: False)" in lines

    def test_enabled_without_hierarchy(self) -> None:
        elem = {"enabledSelf": False}
        lines = _format_element_detail(elem)
        assert "  enabled: False" in lines

    def test_layout_rect(self) -> None:
        elem = {"layout": {"x": 10, "y": 20, "width": 100, "height": 50}}
        lines = _format_element_detail(elem)
        assert "  layout: (10, 20, 100x50)" in lines

    def test_world_bound_rect(self) -> None:
        elem = {"worldBound": {"x": 0, "y": 0, "width": 200, "height": 100}}
        lines = _format_element_detail(elem)
        assert "  worldBound: (0, 0, 200x100)" in lines

    def test_child_count_and_path(self) -> None:
        elem = {"childCount": 5, "path": "/root/panel/btn"}
        lines = _format_element_detail(elem)
        assert "  childCount: 5" in lines
        assert "  path: /root/panel/btn" in lines

    def test_empty_elem_returns_empty(self) -> None:
        assert _format_element_detail({}) == []

    def test_zero_child_count_included(self) -> None:
        elem = {"childCount": 0}
        lines = _format_element_detail(elem)
        assert "  childCount: 0" in lines

    def test_empty_path_excluded(self) -> None:
        elem = {"path": ""}
        assert _format_element_detail(elem) == []

    # --- 異常データ ---

    def test_layout_string_ignored(self) -> None:
        elem = {"layout": "bad"}
        assert _format_element_detail(elem) == []

    def test_layout_none_ignored(self) -> None:
        elem = {"layout": None}
        assert _format_element_detail(elem) == []


class TestFormatElementStyle:
    def test_empty_dict_returns_empty(self) -> None:
        assert _format_element_style({}) == []

    def test_none_returns_empty(self) -> None:
        assert _format_element_style(None) == []

    def test_non_dict_returns_empty(self) -> None:
        assert _format_element_style("not a dict") == []

    def test_single_property(self) -> None:
        lines = _format_element_style({"color": "rgba(255,255,255,1)"})
        assert lines[0] == "  resolvedStyle:"
        assert "    color: rgba(255,255,255,1)" in lines

    def test_multiple_properties(self) -> None:
        data = {"fontSize": 14, "color": "white", "opacity": 1.0}
        lines = _format_element_style(data)
        assert len(lines) == 4  # header + 3 properties
        assert all(not line.startswith("\n") for line in lines)


class TestFormatElementChildren:
    def test_empty_list_returns_empty(self) -> None:
        assert _format_element_children([]) == []

    def test_none_returns_empty(self) -> None:
        assert _format_element_children(None) == []

    def test_non_list_returns_empty(self) -> None:
        assert _format_element_children("not a list") == []

    def test_single_child(self) -> None:
        children = [{"ref": "ref_10", "type": "Label"}]
        lines = _format_element_children(children)
        assert lines[0] == "  children:"
        assert "  ref_10 Label" in lines[1]

    def test_child_with_name(self) -> None:
        children = [{"ref": "ref_11", "type": "Button", "name": "ok"}]
        lines = _format_element_children(children)
        assert '"ok"' in lines[1]

    def test_multiple_children(self) -> None:
        children = [
            {"ref": "ref_20", "type": "Label"},
            {"ref": "ref_21", "type": "Button", "name": "submit"},
        ]
        lines = _format_element_children(children)
        assert len(lines) == 3  # header + 2 children

    # --- 異常データ ---

    def test_non_dict_child_skipped(self) -> None:
        children = [None, "bad", {"ref": "ref_30", "type": "Label"}]
        lines = _format_element_children(children)
        assert len(lines) == 2  # header + 1 valid child
        assert "ref_30" in lines[1]

    def test_empty_dict_child_handled(self) -> None:
        children = [{}]
        lines = _format_element_children(children)
        assert len(lines) == 2  # header + 1 child with defaults


class TestFormatInspectElement:
    def test_minimal_element(self) -> None:
        elem = {"ref": "ref_1", "type": "VisualElement"}
        lines = _format_inspect_element(elem)
        assert lines == ["ref_1 VisualElement"]

    def test_full_element(self) -> None:
        elem = {
            "ref": "ref_5",
            "type": "Button",
            "name": "play",
            "classes": ["primary"],
            "visible": True,
            "enabledSelf": True,
            "layout": {"x": 0, "y": 0, "width": 80, "height": 30},
            "childCount": 1,
            "resolvedStyle": {"fontSize": 12},
            "children": [{"ref": "ref_6", "type": "Label", "name": "text"}],
        }
        lines = _format_inspect_element(elem)
        assert 'ref_5 Button "play"' in lines
        assert "  classes: .primary" in lines
        assert "  visible: True" in lines
        assert "  layout: (0, 0, 80x30)" in lines
        # blank line before resolvedStyle section
        style_idx = lines.index("  resolvedStyle:")
        assert lines[style_idx - 1] == ""
        assert "    fontSize: 12" in lines
        # blank line before children section
        children_idx = lines.index("  children:")
        assert lines[children_idx - 1] == ""

    def test_no_style_no_children(self) -> None:
        elem = {"ref": "ref_7", "type": "Toggle", "visible": False}
        lines = _format_inspect_element(elem)
        assert "  resolvedStyle:" not in lines
        assert "  children:" not in lines

    def test_style_without_children(self) -> None:
        elem = {
            "ref": "ref_8",
            "type": "Label",
            "resolvedStyle": {"color": "white"},
        }
        lines = _format_inspect_element(elem)
        assert "  resolvedStyle:" in lines
        assert "  children:" not in lines

    def test_children_without_style(self) -> None:
        elem = {
            "ref": "ref_9",
            "type": "VisualElement",
            "children": [{"ref": "ref_10", "type": "Label"}],
        }
        lines = _format_inspect_element(elem)
        assert "  children:" in lines
        assert "  resolvedStyle:" not in lines


class TestFormatQueryMatch:
    def test_basic_match(self) -> None:
        elem = {"ref": "ref_1", "type": "Button"}
        lines = _format_query_match(elem)
        assert lines[0] == "  ref_1 Button"
        assert lines[-1] == ""  # trailing empty line

    def test_with_name_and_classes(self) -> None:
        elem = {"ref": "ref_2", "type": "Label", "name": "title", "classes": ["bold"]}
        lines = _format_query_match(elem)
        assert lines[0] == '  ref_2 Label "title" .bold'

    def test_with_path(self) -> None:
        elem = {"ref": "ref_3", "type": "Button", "path": "/root/btn"}
        lines = _format_query_match(elem)
        assert any("path: /root/btn" in line for line in lines)

    def test_with_layout(self) -> None:
        elem = {
            "ref": "ref_4",
            "type": "Slider",
            "layout": {"x": 5, "y": 10, "width": 200, "height": 20},
        }
        lines = _format_query_match(elem)
        assert any("layout: (5, 10, 200x20)" in line for line in lines)

    def test_no_path_no_layout(self) -> None:
        elem = {"ref": "ref_5", "type": "Toggle"}
        lines = _format_query_match(elem)
        # header + trailing empty
        assert len(lines) == 2

    def test_with_path_and_layout(self) -> None:
        elem = {
            "ref": "ref_6",
            "type": "Button",
            "path": "/root/btn",
            "layout": {"x": 0, "y": 0, "width": 100, "height": 40},
        }
        lines = _format_query_match(elem)
        # header + path + layout + trailing empty
        assert len(lines) == 4

    # --- 異常データ ---

    def test_classes_none_ignored(self) -> None:
        elem = {"ref": "ref_7", "type": "Button", "classes": None}
        lines = _format_query_match(elem)
        assert lines[0] == "  ref_7 Button"

    def test_layout_string_ignored(self) -> None:
        elem = {"ref": "ref_8", "type": "Button", "layout": "bad"}
        lines = _format_query_match(elem)
        assert not any("layout" in line for line in lines)

    def test_layout_empty_dict_ignored(self) -> None:
        elem = {"ref": "ref_9", "type": "Button", "layout": {}}
        lines = _format_query_match(elem)
        assert not any("layout" in line for line in lines)
