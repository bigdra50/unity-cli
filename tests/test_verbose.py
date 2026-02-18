"""Tests for verbose output helpers: masking and truncation."""

from __future__ import annotations

from unity_cli.cli.app import _VERBOSE_MAX_LEN, _mask_sensitive, _truncate_json


class TestMaskSensitive:
    def test_masks_password_key(self) -> None:
        assert _mask_sensitive({"password": "FAKE_VALUE"}) == {"password": "***"}

    def test_masks_token_key(self) -> None:
        assert _mask_sensitive({"Token": "FAKE_VALUE"}) == {"Token": "***"}

    def test_masks_api_key_key(self) -> None:
        assert _mask_sensitive({"api_key": "FAKE_VALUE"}) == {"api_key": "***"}

    def test_preserves_normal_keys(self) -> None:
        data = {"command": "play", "id": "123"}
        assert _mask_sensitive(data) == data

    def test_nested_dict(self) -> None:
        data = {"params": {"secret": "FAKE_VALUE", "name": "visible"}}
        assert _mask_sensitive(data) == {"params": {"secret": "***", "name": "visible"}}

    def test_list_of_dicts(self) -> None:
        data = [{"password": "x"}, {"name": "y"}]
        assert _mask_sensitive(data) == [{"password": "***"}, {"name": "y"}]

    def test_scalar_passthrough(self) -> None:
        assert _mask_sensitive(42) == 42
        assert _mask_sensitive("hello") == "hello"
        assert _mask_sensitive(None) is None


class TestTruncateJson:
    def test_short_text_unchanged(self) -> None:
        text = '{"ok": true}'
        assert _truncate_json(text) == text

    def test_long_text_truncated(self) -> None:
        text = "x" * (_VERBOSE_MAX_LEN + 100)
        result = _truncate_json(text)
        assert len(result) < len(text)
        assert "truncated" in result
        assert str(len(text)) in result

    def test_exact_limit_unchanged(self) -> None:
        text = "a" * _VERBOSE_MAX_LEN
        assert _truncate_json(text) == text
