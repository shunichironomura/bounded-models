from types import NoneType
from typing import Annotated

import pytest
from pydantic.fields import FieldInfo

from bounded_models import FieldHandlerRegistry, NumericFieldHandler, SequenceFieldHandler, StringFieldHandler


@pytest.fixture
def handler() -> SequenceFieldHandler:
    """Create a sequence handler instance."""
    return SequenceFieldHandler()


@pytest.fixture
def registry(handler: SequenceFieldHandler) -> FieldHandlerRegistry:
    """Create a type handler registry instance."""
    return FieldHandlerRegistry(handlers=[handler, NumericFieldHandler(), StringFieldHandler()])


_BOUNDED_FIELDS = [
    FieldInfo(annotation=list[Annotated[str, FieldInfo(annotation=NoneType, max_length=10)]], max_length=5),
    FieldInfo(
        annotation=tuple[
            Annotated[int, FieldInfo(annotation=NoneType, ge=0, le=100)],
            Annotated[int, FieldInfo(annotation=NoneType, ge=0, le=100)],
        ],
    ),
    FieldInfo(
        annotation=tuple[Annotated[int, FieldInfo(annotation=NoneType, ge=0, le=100)], ...],
        max_length=3,
    ),
]

_UNBOUNDED_FIELDS = [
    FieldInfo(annotation=list),
    FieldInfo(annotation=list[int]),
    FieldInfo(annotation=list[Annotated[int, FieldInfo(annotation=NoneType, ge=0)]], max_length=10),
    FieldInfo(annotation=list[Annotated[int, FieldInfo(annotation=NoneType, ge=0, le=100)]]),
    FieldInfo(
        annotation=tuple[Annotated[int, FieldInfo(annotation=NoneType, ge=0, le=100)], ...],
    ),
]

_INVALID_FIELDS = [
    FieldInfo(annotation=str),
]


@pytest.mark.xfail
@pytest.mark.parametrize(
    ("field_info", "can_handle", "bounded"),
    [(field_info, True, True) for field_info in _BOUNDED_FIELDS]
    + [(field_info, True, False) for field_info in _UNBOUNDED_FIELDS]
    + [(field_info, False, None) for field_info in _INVALID_FIELDS],
)
def test_sequence_handler(
    handler: SequenceFieldHandler,
    registry: FieldHandlerRegistry,
    *,
    field_info: FieldInfo,
    can_handle: bool,
    bounded: bool | None,
) -> None:
    """Test sequence handler for boundedness."""
    assert handler.can_handle(field_info) == can_handle
    if can_handle:
        assert handler.check_boundedness(field_info, registry) == bounded
