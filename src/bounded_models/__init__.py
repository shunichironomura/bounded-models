"""Top-level package for bounded-models."""

from __future__ import annotations

__all__ = [
    "BaseModelFieldHandler",
    "BoundedModel",
    "FieldHandler",
    "FieldHandlerRegistry",
    "LiteralFieldHandler",
    "NumericFieldHandler",
    "OptionalFieldHandler",
    "SequenceFieldHandler",
    "StringFieldHandler",
    "is_field_bounded",
    "is_model_bounded",
]

from ._core import BoundedModel
from ._handlers import (
    BaseModelFieldHandler,
    FieldHandler,
    LiteralFieldHandler,
    NumericFieldHandler,
    OptionalFieldHandler,
    SequenceFieldHandler,
    StringFieldHandler,
)
from ._registry import FieldHandlerRegistry, is_field_bounded, is_model_bounded
