import pytest
from pydantic.fields import FieldInfo

from bounded_models import BoundednessCheckerRegistry, NumericChecker


@pytest.fixture
def checker() -> NumericChecker:
    """Create a numeric checker instance."""
    return NumericChecker()


@pytest.fixture
def registry(checker: NumericChecker) -> BoundednessCheckerRegistry:
    """Create a type checker registry instance."""
    return BoundednessCheckerRegistry(checkers=[checker])


_BOUNDED_FIELDS = [
    FieldInfo(annotation=float, gt=0.0, le=1.0),
    FieldInfo(annotation=int, ge=0, lt=100),
]

_UNBOUNDED_FIELDS = [
    FieldInfo(annotation=float),
    FieldInfo(annotation=int),
    FieldInfo(annotation=float, ge=0.0),
    FieldInfo(annotation=float, le=100.0),
    FieldInfo(annotation=int, ge=0),
    FieldInfo(annotation=int, le=100),
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
def test_numeric_checker(
    checker: NumericChecker,
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
