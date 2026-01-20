"""Top-level package for bounded-models."""

from __future__ import annotations

__all__ = [
    "UNSET",
    "BaseModelFieldHandler",
    "BoundedModel",
    "EnumFieldHandler",
    "FieldHandler",
    "FieldHandlerRegistry",
    "FieldOverride",
    "LiteralFieldHandler",
    "MissingDefaultError",
    "NumericFieldHandler",
    "OptionalFieldHandler",
    "SequenceFieldHandler",
    "StringFieldHandler",
    "UnboundedFieldError",
    "field_dimensions",
    "is_field_bounded",
    "is_model_bounded",
    "model_dimensions",
]

from ._handlers import (
    BaseModelFieldHandler,
    EnumFieldHandler,
    FieldHandler,
    LiteralFieldHandler,
    NumericFieldHandler,
    OptionalFieldHandler,
    SequenceFieldHandler,
    StringFieldHandler,
)
from ._model import BoundedModel
from ._overrides import UNSET, FieldOverride
from ._registry import (
    FieldHandlerRegistry,
    MissingDefaultError,
    UnboundedFieldError,
    field_dimensions,
    is_field_bounded,
    is_model_bounded,
    model_dimensions,
)
