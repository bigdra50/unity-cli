"""Tests for unity_cli/models.py - Domain Models"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from unity_cli.models import Color, PaginationOptions, TestFilterOptions, Vector3


class TestVector3:
    """Vector3 モデルのテスト"""

    def test_default_values(self) -> None:
        """デフォルトは (0, 0, 0)。"""
        sut = Vector3()
        assert sut.x == 0.0
        assert sut.y == 0.0
        assert sut.z == 0.0

    def test_custom_values(self) -> None:
        """任意の値で生成できる。"""
        sut = Vector3(x=1.5, y=-2.3, z=100.0)
        assert sut.x == 1.5
        assert sut.y == -2.3
        assert sut.z == 100.0

    def test_frozen(self) -> None:
        """frozen=True により書き換え不可。"""
        sut = Vector3(x=1.0)
        with pytest.raises(ValidationError):
            sut.x = 2.0  # type: ignore[misc]

    def test_hashable(self) -> None:
        """frozen なので hash 可能。"""
        a = Vector3(x=1.0, y=2.0, z=3.0)
        b = Vector3(x=1.0, y=2.0, z=3.0)
        assert hash(a) == hash(b)
        assert a == b

    def test_to_list(self) -> None:
        """[x, y, z] リストに変換。"""
        sut = Vector3(x=1.0, y=2.0, z=3.0)
        assert sut.to_list() == [1.0, 2.0, 3.0]

    @pytest.mark.parametrize(
        ("input_list", "expected"),
        [
            ([1.0, 2.0, 3.0], Vector3(x=1.0, y=2.0, z=3.0)),
            ([1.0, 2.0, 3.0, 4.0], Vector3(x=1.0, y=2.0, z=3.0)),
            ([1.0, 2.0, 3.0, 4.0, 5.0], Vector3(x=1.0, y=2.0, z=3.0)),
        ],
        ids=["exact-3", "extra-elements-4", "extra-elements-5"],
    )
    def test_from_list_valid(self, input_list: list[float], expected: Vector3) -> None:
        """要素数 >= 3 ならば先頭3つで生成。"""
        assert Vector3.from_list(input_list) == expected

    @pytest.mark.parametrize(
        "input_list",
        [[], [1.0], [1.0, 2.0]],
        ids=["empty", "one-element", "two-elements"],
    )
    def test_from_list_returns_default_when_insufficient(self, input_list: list[float]) -> None:
        """要素数 < 3 はデフォルト値を返す。"""
        assert Vector3.from_list(input_list) == Vector3()

    def test_to_list_roundtrip(self) -> None:
        """to_list -> from_list で同じ値を復元。"""
        original = Vector3(x=3.14, y=-1.0, z=0.0)
        assert Vector3.from_list(original.to_list()) == original


class TestColor:
    """Color モデルのテスト"""

    def test_default_values(self) -> None:
        """デフォルトは白 (1, 1, 1, 1)。"""
        sut = Color()
        assert sut.r == 1.0
        assert sut.g == 1.0
        assert sut.b == 1.0
        assert sut.a == 1.0

    def test_custom_values(self) -> None:
        """任意の RGBA 値で生成。"""
        sut = Color(r=0.5, g=0.3, b=0.1, a=0.8)
        assert sut.r == 0.5
        assert sut.a == 0.8

    def test_frozen(self) -> None:
        """frozen=True により書き換え不可。"""
        sut = Color()
        with pytest.raises(ValidationError):
            sut.r = 0.5  # type: ignore[misc]

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("r", -0.1),
            ("g", 1.1),
            ("b", -1.0),
            ("a", 2.0),
        ],
    )
    def test_out_of_range_raises(self, field: str, value: float) -> None:
        """0.0-1.0 範囲外は ValidationError。"""
        with pytest.raises(ValidationError):
            Color(**{field: value})

    @pytest.mark.parametrize(
        ("value",),
        [(0.0,), (0.5,), (1.0,)],
    )
    def test_boundary_values_accepted(self, value: float) -> None:
        """境界値 0.0, 0.5, 1.0 は有効。"""
        sut = Color(r=value, g=value, b=value, a=value)
        assert sut.r == value

    def test_to_list(self) -> None:
        """[r, g, b, a] リストに変換。"""
        sut = Color(r=0.1, g=0.2, b=0.3, a=0.4)
        assert sut.to_list() == [0.1, 0.2, 0.3, 0.4]

    @pytest.mark.parametrize(
        ("input_list", "expected"),
        [
            ([0.1, 0.2, 0.3, 0.4], Color(r=0.1, g=0.2, b=0.3, a=0.4)),
            ([0.1, 0.2, 0.3, 0.4, 0.5], Color(r=0.1, g=0.2, b=0.3, a=0.4)),
            ([0.1, 0.2, 0.3], Color(r=0.1, g=0.2, b=0.3, a=1.0)),
        ],
        ids=["rgba-4", "extra-elements", "rgb-3-default-alpha"],
    )
    def test_from_list_valid(self, input_list: list[float], expected: Color) -> None:
        """要素数 >= 3 ならば適切に生成。"""
        assert Color.from_list(input_list) == expected

    @pytest.mark.parametrize(
        "input_list",
        [[], [0.1], [0.1, 0.2]],
        ids=["empty", "one-element", "two-elements"],
    )
    def test_from_list_returns_default_when_insufficient(self, input_list: list[float]) -> None:
        """要素数 < 3 はデフォルト値を返す。"""
        assert Color.from_list(input_list) == Color()

    def test_to_list_roundtrip(self) -> None:
        """to_list -> from_list で同じ値を復元。"""
        original = Color(r=0.2, g=0.4, b=0.6, a=0.8)
        assert Color.from_list(original.to_list()) == original


class TestPaginationOptions:
    """PaginationOptions モデルのテスト"""

    def test_defaults(self) -> None:
        """デフォルト値: page_size=50, cursor=None, max_nodes=None。"""
        sut = PaginationOptions()
        assert sut.page_size == 50
        assert sut.cursor is None
        assert sut.max_nodes is None

    def test_custom_values(self) -> None:
        """任意の値で生成。"""
        sut = PaginationOptions(page_size=100, cursor=5, max_nodes=200)
        assert sut.page_size == 100
        assert sut.cursor == 5
        assert sut.max_nodes == 200

    def test_cursor_as_string(self) -> None:
        """cursor は str でも指定可能。"""
        sut = PaginationOptions(cursor="abc123")
        assert sut.cursor == "abc123"

    @pytest.mark.parametrize(
        "page_size",
        [0, -1],
        ids=["zero", "negative"],
    )
    def test_page_size_must_be_positive(self, page_size: int) -> None:
        """page_size <= 0 は ValidationError。"""
        with pytest.raises(ValidationError):
            PaginationOptions(page_size=page_size)

    def test_page_size_max_1000(self) -> None:
        """page_size > 1000 は ValidationError。"""
        with pytest.raises(ValidationError):
            PaginationOptions(page_size=1001)

    def test_page_size_boundary_1000(self) -> None:
        """page_size = 1000 は有効。"""
        sut = PaginationOptions(page_size=1000)
        assert sut.page_size == 1000

    def test_page_size_boundary_1(self) -> None:
        """page_size = 1 は有効。"""
        sut = PaginationOptions(page_size=1)
        assert sut.page_size == 1

    def test_max_nodes_must_be_positive(self) -> None:
        """max_nodes <= 0 は ValidationError。"""
        with pytest.raises(ValidationError):
            PaginationOptions(max_nodes=0)

    def test_frozen(self) -> None:
        """frozen=True により書き換え不可。"""
        sut = PaginationOptions()
        with pytest.raises(ValidationError):
            sut.page_size = 10  # type: ignore[misc]


class TestTestFilterOptions:
    """TestFilterOptions モデルのテスト"""

    def test_defaults_all_none(self) -> None:
        """デフォルトは全フィルタ None。"""
        sut = TestFilterOptions()
        assert sut.test_names is None
        assert sut.group_names is None
        assert sut.category_names is None
        assert sut.assembly_names is None

    def test_with_test_names(self) -> None:
        """test_names を指定。"""
        sut = TestFilterOptions(test_names=["Ns.Tests.TestA", "Ns.Tests.TestB"])
        assert sut.test_names is not None
        assert len(sut.test_names) == 2

    def test_with_all_filters(self) -> None:
        """全フィルタを同時に指定。"""
        sut = TestFilterOptions(
            test_names=["Test1"],
            group_names=[".*Integration.*"],
            category_names=["Smoke"],
            assembly_names=["Game.Tests"],
        )
        assert sut.test_names is not None
        assert sut.group_names is not None
        assert sut.category_names is not None
        assert sut.assembly_names is not None

    def test_empty_sequences(self) -> None:
        """空シーケンスも有効。"""
        sut = TestFilterOptions(test_names=[], group_names=[])
        assert sut.test_names is not None
        assert len(sut.test_names) == 0

    def test_frozen(self) -> None:
        """frozen=True により書き換え不可。"""
        sut = TestFilterOptions()
        with pytest.raises(ValidationError):
            sut.test_names = ["x"]  # type: ignore[misc]
