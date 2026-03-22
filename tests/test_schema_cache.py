"""Tests for unity_cli/api/schema_cache.py"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from unity_cli.api.schema_cache import SchemaCache


@pytest.fixture
def cache_dir(tmp_path: Path) -> Path:
    return tmp_path / "api-schema"


@pytest.fixture
def sut(cache_dir: Path) -> SchemaCache:
    return SchemaCache(cache_dir=cache_dir)


@pytest.fixture
def sample_schema() -> dict[str, Any]:
    return {
        "version": "6000.2.6f2",
        "methods": [
            {
                "type": "UnityEditor.AssetDatabase",
                "method": "Refresh",
                "returnType": "Void",
                "parameters": [],
            }
        ],
        "total": 1,
    }


class TestGet:
    def test_returns_none_when_not_cached(self, sut: SchemaCache) -> None:
        assert sut.get("6000.2.6f2") is None

    def test_returns_schema_after_put(self, sut: SchemaCache, sample_schema: dict[str, Any]) -> None:
        sut.put("6000.2.6f2", sample_schema)
        result = sut.get("6000.2.6f2")
        assert result == sample_schema

    def test_returns_none_for_corrupt_json(self, sut: SchemaCache, cache_dir: Path) -> None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / "6000.2.6f2.json").write_text("not json")
        assert sut.get("6000.2.6f2") is None


class TestPut:
    def test_creates_cache_directory(self, sut: SchemaCache, cache_dir: Path, sample_schema: dict[str, Any]) -> None:
        assert not cache_dir.exists()
        sut.put("6000.2.6f2", sample_schema)
        assert cache_dir.exists()

    def test_overwrites_existing_cache(self, sut: SchemaCache, sample_schema: dict[str, Any]) -> None:
        sut.put("6000.2.6f2", sample_schema)
        updated = {**sample_schema, "total": 999}
        sut.put("6000.2.6f2", updated)
        result = sut.get("6000.2.6f2")
        assert result is not None
        assert result["total"] == 999


class TestHas:
    def test_false_when_not_cached(self, sut: SchemaCache) -> None:
        assert sut.has("6000.2.6f2") is False

    def test_true_after_put(self, sut: SchemaCache, sample_schema: dict[str, Any]) -> None:
        sut.put("6000.2.6f2", sample_schema)
        assert sut.has("6000.2.6f2") is True

    def test_different_versions_independent(self, sut: SchemaCache, sample_schema: dict[str, Any]) -> None:
        sut.put("6000.2.6f2", sample_schema)
        assert sut.has("6000.1.1f1") is False
