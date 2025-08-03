from typing import Literal

import pytest
from pydantic import BaseModel
from pydantic.fields import FieldInfo

from bounded_models import BaseModelFieldHandler, FieldHandlerRegistry, LiteralFieldHandler, NumericFieldHandler


@pytest.fixture
def handler() -> BaseModelFieldHandler:
    """Create a BaseModel handler instance."""
    return BaseModelFieldHandler()


@pytest.fixture
def registry(handler: BaseModelFieldHandler) -> FieldHandlerRegistry:
    """Create a type handler registry instance."""
    return FieldHandlerRegistry(handlers=[handler, LiteralFieldHandler(), NumericFieldHandler()])


class BoundedChildModel(BaseModel):
    """A simple bounded child model for testing."""

    value: Literal[1, 2, 3]


class BoundedChildModelWithManyFields(BaseModel):
    """A bounded child model with many fields for testing."""

    value1: Literal[1, 2, 3]
    value2: Literal["a", "b", "c"]
    value3: Literal[True, False]


class UnboundedChildModel(BaseModel):
    """A simple unbounded child model for testing."""

    value: int


_BOUNDED_FIELDS = [
    (FieldInfo(annotation=BoundedChildModel), 1),
    (FieldInfo(annotation=BoundedChildModelWithManyFields), 3),
]

_UNBOUNDED_FIELDS = [
    (FieldInfo(annotation=UnboundedChildModel), 1),
]

_INVALID_FIELDS = [
    FieldInfo(annotation=str),
]


@pytest.mark.parametrize(
    ("field_info", "can_handle", "bounded", "n_dimensions"),
    [(field_info, True, True, dim) for (field_info, dim) in _BOUNDED_FIELDS]
    + [(field_info, True, False, dim) for (field_info, dim) in _UNBOUNDED_FIELDS]
    + [(field_info, False, None, None) for field_info in _INVALID_FIELDS],
)
def test_base_model_handler(
    handler: BaseModelFieldHandler,
    registry: FieldHandlerRegistry,
    *,
    field_info: FieldInfo,
    can_handle: bool,
    bounded: bool | None,
    n_dimensions: int | None,
) -> None:
    """Test numeric handler for boundedness."""
    assert handler.can_handle(field_info) == can_handle
    if can_handle:
        assert handler.check_boundedness(field_info, registry) == bounded
        assert handler.n_dimensions(field_info, registry) == n_dimensions
