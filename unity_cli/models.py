"""
Unity CLI Domain Models
========================

Pydantic v2 models for Unity CLI domain types.
All models are immutable (frozen) for safety and hashability.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field


class Vector3(BaseModel):
    """Immutable 3D vector for position, rotation, scale."""

    model_config = ConfigDict(frozen=True)

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def to_list(self) -> list[float]:
        """Convert to [x, y, z] list."""
        return [self.x, self.y, self.z]

    @classmethod
    def from_list(cls, v: Sequence[float]) -> Self:
        """Create from [x, y, z] list. Returns default if invalid."""
        if len(v) >= 3:
            return cls(x=v[0], y=v[1], z=v[2])
        return cls()


class Color(BaseModel):
    """Immutable RGBA color. Values are clamped to 0.0-1.0 range."""

    model_config = ConfigDict(frozen=True)

    r: Annotated[float, Field(ge=0.0, le=1.0)] = 1.0
    g: Annotated[float, Field(ge=0.0, le=1.0)] = 1.0
    b: Annotated[float, Field(ge=0.0, le=1.0)] = 1.0
    a: Annotated[float, Field(ge=0.0, le=1.0)] = 1.0

    def to_list(self) -> list[float]:
        """Convert to [r, g, b, a] list."""
        return [self.r, self.g, self.b, self.a]

    @classmethod
    def from_list(cls, v: Sequence[float]) -> Self:
        """Create from [r, g, b] or [r, g, b, a] list. Returns default if invalid."""
        if len(v) >= 4:
            return cls(r=v[0], g=v[1], b=v[2], a=v[3])
        if len(v) >= 3:
            return cls(r=v[0], g=v[1], b=v[2])
        return cls()


class PaginationOptions(BaseModel):
    """Reusable pagination settings."""

    model_config = ConfigDict(frozen=True)

    page_size: Annotated[int, Field(gt=0, le=1000)] = 50
    cursor: int | str | None = None
    max_nodes: Annotated[int | None, Field(gt=0)] = None


class TestFilterOptions(BaseModel):
    """Test filtering options.

    When multiple filters are specified, they combine with AND logic.
    Tests must match ALL specified filters to be included.

    Attributes:
        test_names: Full test names (exact match, e.g., "MyNamespace.MyTests.TestMethod")
        group_names: Regex patterns for test names
        category_names: NUnit category names ([Category] attribute)
        assembly_names: Assembly names to filter by
    """

    model_config = ConfigDict(frozen=True)

    test_names: Sequence[str] | None = None
    group_names: Sequence[str] | None = None
    category_names: Sequence[str] | None = None
    assembly_names: Sequence[str] | None = None
