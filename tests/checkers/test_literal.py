from typing import Literal

import pytest
from pydantic.fields import FieldInfo

from bounded_models import FieldHandlerRegistry, LiteralFieldHandler


@pytest.fixture
def handler() -> LiteralFieldHandler:
    """Create a string handler instance."""
    return LiteralFieldHandler()


@pytest.fixture
def registry(handler: LiteralFieldHandler) -> FieldHandlerRegistry:
    """Create a type handler registry instance."""
    return FieldHandlerRegistry(handlers=[handler])


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
def test_literal_handler(
    handler: LiteralFieldHandler,
    registry: FieldHandlerRegistry,
    *,
    field_info: FieldInfo,
    can_handle: bool,
    bounded: bool | None,
) -> None:
    """Test numeric handler for boundedness."""
    assert handler.can_handle(field_info) == can_handle
    if can_handle:
        assert handler.check_boundedness(field_info, registry) == bounded
        assert handler.n_dimensions(field_info, registry) == 1
