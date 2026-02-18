"""Tests for _parse_cli_value JSON-first parsing."""

from __future__ import annotations

import pytest

from unity_cli.cli.helpers import _parse_cli_value


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # JSON booleans
        ("true", True),
        ("false", False),
        # Legacy Python booleans
        ("True", True),
        ("False", False),
        ("TRUE", True),
        # Integers
        ("42", 42),
        ("-1", -1),
        ("0", 0),
        # Floats
        ("3.14", 3.14),
        ("-0.5", -0.5),
        # JSON quoted string → str (not bool)
        ('"true"', "true"),
        ('"false"', "false"),
        ('"hello"', "hello"),
        ('"42"', "42"),
        # JSON array
        ("[1,2,3]", [1, 2, 3]),
        ('["a","b"]', ["a", "b"]),
        # JSON object
        ('{"r":1,"g":0,"b":0}', {"r": 1, "g": 0, "b": 0}),
        # Bare string
        ("hello", "hello"),
        ("some text", "some text"),
        # Edge cases
        ("", ""),
        ("null", None),
    ],
    ids=[
        "json-true",
        "json-false",
        "legacy-True",
        "legacy-False",
        "legacy-TRUE",
        "int-42",
        "int-neg",
        "int-zero",
        "float-pi",
        "float-neg",
        "quoted-true-str",
        "quoted-false-str",
        "quoted-hello",
        "quoted-42",
        "array-ints",
        "array-strs",
        "object",
        "bare-str",
        "bare-str-space",
        "empty",
        "json-null",
    ],
)
def test_parse_cli_value(raw: str, expected: object) -> None:
    assert _parse_cli_value(raw) == expected


def test_parse_cli_value_types() -> None:
    assert isinstance(_parse_cli_value("42"), int)
    assert isinstance(_parse_cli_value("3.14"), float)
    assert isinstance(_parse_cli_value("true"), bool)
    assert isinstance(_parse_cli_value('"true"'), str)
