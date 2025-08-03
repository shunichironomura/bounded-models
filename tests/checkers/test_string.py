import pytest
from pydantic.fields import FieldInfo

from bounded_models import BoundednessCheckerRegistry, StringChecker


@pytest.fixture
def checker() -> StringChecker:
    """Create a string checker instance."""
    return StringChecker()


@pytest.fixture
def registry(checker: StringChecker) -> BoundednessCheckerRegistry:
    """Create a type checker registry instance."""
    return BoundednessCheckerRegistry(checkers=[checker])


_BOUNDED_FIELDS = [
    FieldInfo(annotation=str, min_length=1, max_length=100),
    FieldInfo(annotation=str, max_length=50),
]

_UNBOUNDED_FIELDS = [
    FieldInfo(annotation=str),
    FieldInfo(annotation=str, min_length=1),
]

_INVALID_FIELDS = [
    FieldInfo(annotation=int),
]


@pytest.mark.parametrize(
    ("field_info", "can_handle", "bounded"),
    [(field_info, True, True) for field_info in _BOUNDED_FIELDS]
    + [(field_info, True, False) for field_info in _UNBOUNDED_FIELDS]
    + [(field_info, False, None) for field_info in _INVALID_FIELDS],
)
def test_string_checker(
    checker: StringChecker,
    registry: BoundednessCheckerRegistry,
    *,
    field_info: FieldInfo,
    can_handle: bool,
    bounded: bool | None,
) -> None:
    """Test string checker for boundedness."""
    assert checker.can_handle(field_info) == can_handle
    if can_handle:
        assert checker.check(field_info, registry) == bounded
