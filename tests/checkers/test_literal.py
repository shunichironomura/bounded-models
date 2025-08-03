from typing import Literal

import pytest
from pydantic.fields import FieldInfo

from bounded_models import BoundednessCheckerRegistry, LiteralChecker


@pytest.fixture
def checker() -> LiteralChecker:
    """Create a string checker instance."""
    return LiteralChecker()


@pytest.fixture
def registry(checker: LiteralChecker) -> BoundednessCheckerRegistry:
    """Create a type checker registry instance."""
    return BoundednessCheckerRegistry(checkers=[checker])


_BOUNDED_FIELDS = [
    FieldInfo(annotation=Literal[1, 2, 3]),  # type: ignore[arg-type]
    FieldInfo(annotation=Literal["a", "b"]),  # type: ignore[arg-type]
]

_UNBOUNDED_FIELDS: list[FieldInfo] = []

_INVALID_FIELDS = [
    FieldInfo(annotation=str),
]


@pytest.mark.parametrize(
    ("field_info", "can_handle", "bounded"),
    [(field_info, True, True) for field_info in _BOUNDED_FIELDS]
    + [(field_info, True, False) for field_info in _UNBOUNDED_FIELDS]
    + [(field_info, False, None) for field_info in _INVALID_FIELDS],
)
def test_literal_checker(
    checker: LiteralChecker,
    registry: BoundednessCheckerRegistry,
    *,
    field_info: FieldInfo,
    can_handle: bool,
    bounded: bool | None,
) -> None:
    """Test numeric checker for boundedness."""
    assert checker.can_handle(field_info) == can_handle
    if can_handle:
        assert checker.check(field_info, registry) == bounded
