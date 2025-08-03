from types import NoneType
from typing import Annotated

import pytest
from pydantic.fields import FieldInfo

from bounded_models import BoundednessCheckerRegistry, NumericChecker, SequenceChecker


@pytest.fixture
def checker() -> SequenceChecker:
    """Create a sequence checker instance."""
    return SequenceChecker()


@pytest.fixture
def registry(checker: SequenceChecker) -> BoundednessCheckerRegistry:
    """Create a type checker registry instance."""
    return BoundednessCheckerRegistry(checkers=[checker, NumericChecker()])


_BOUNDED_FIELDS = [
    FieldInfo(annotation=list[Annotated[str, FieldInfo(annotation=NoneType, max_length=10)]], max_length=5),
]

_UNBOUNDED_FIELDS = [
    FieldInfo(annotation=list),
    FieldInfo(annotation=list[int]),
]

_INVALID_FIELDS = [
    FieldInfo(annotation=str),
]


@pytest.mark.parametrize(
    ("field_info", "can_handle", "bounded"),
    [(field_info, True, True) for field_info in _BOUNDED_FIELDS]
    + [(field_info, True, False) for field_info in _UNBOUNDED_FIELDS]
    + [(field_info, False, None) for field_info in _INVALID_FIELDS],
)
def test_sequence_checker(
    checker: SequenceChecker,
    registry: BoundednessCheckerRegistry,
    *,
    field_info: FieldInfo,
    can_handle: bool,
    bounded: bool | None,
) -> None:
    """Test sequence checker for boundedness."""
    assert checker.can_handle(field_info) == can_handle
    if can_handle:
        assert checker.check(field_info, registry) == bounded
