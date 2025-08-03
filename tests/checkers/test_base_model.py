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


class UnboundedChildModel(BaseModel):
    """A simple unbounded child model for testing."""

    value: int


_BOUNDED_FIELDS = [
    FieldInfo(annotation=BoundedChildModel),
]

_UNBOUNDED_FIELDS = [
    FieldInfo(annotation=UnboundedChildModel),
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
def test_base_model_handler(
    handler: BaseModelFieldHandler,
    registry: FieldHandlerRegistry,
    *,
    field_info: FieldInfo,
    can_handle: bool,
    bounded: bool | None,
) -> None:
    """Test numeric handler for boundedness."""
    assert handler.can_handle(field_info) == can_handle
    if can_handle:
        assert handler.check(field_info, registry) == bounded
