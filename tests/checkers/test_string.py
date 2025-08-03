import pytest
from pydantic.fields import FieldInfo

from bounded_models import FieldHandlerRegistry, StringFieldHandler


@pytest.fixture
def handler() -> StringFieldHandler:
    """Create a string handler instance."""
    return StringFieldHandler()


@pytest.fixture
def registry(handler: StringFieldHandler) -> FieldHandlerRegistry:
    """Create a type handler registry instance."""
    return FieldHandlerRegistry(handlers=[handler])


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
def test_string_handler(
    handler: StringFieldHandler,
    registry: FieldHandlerRegistry,
    *,
    field_info: FieldInfo,
    can_handle: bool,
    bounded: bool | None,
) -> None:
    """Test string handler for boundedness."""
    assert handler.can_handle(field_info) == can_handle
    if can_handle:
        assert handler.check_boundedness(field_info, registry) == bounded
