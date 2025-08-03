"""Boundedness checkers."""

from __future__ import annotations

import inspect
import types
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar, Literal, Union, get_args, get_origin

import annotated_types
from pydantic import BaseModel
from pydantic.fields import FieldInfo

if TYPE_CHECKING:
    from ._registry import BoundednessCheckerRegistry


class BoundednessChecker(ABC):
    """Abstract base class for type checkers with recursive support."""

    @abstractmethod
    def can_handle(self, field_info: FieldInfo) -> bool:
        """Check if this checker can handle the given field."""
        raise NotImplementedError

    @abstractmethod
    def check(self, field_info: FieldInfo, registry: BoundednessCheckerRegistry) -> bool:
        """Check if the field is properly bounded, using registry for recursive checks."""
        raise NotImplementedError


class NumericChecker(BoundednessChecker):
    """Checker for numeric types (int, float)."""

    def can_handle(self, field_info: FieldInfo) -> bool:
        """Check if the field is a numeric type."""
        return field_info.annotation in (int, float)

    def check(self, field_info: FieldInfo, registry: BoundednessCheckerRegistry) -> bool:  # noqa: ARG002
        """Check if numeric field has both lower and upper bounds."""
        has_lower = any(isinstance(m, (annotated_types.Ge, annotated_types.Gt)) for m in field_info.metadata)
        has_upper = any(isinstance(m, (annotated_types.Le, annotated_types.Lt)) for m in field_info.metadata)
        return has_lower and has_upper


class StringChecker(BoundednessChecker):
    """Checker for string types.

    It checks for max_length constraint.
    """

    def can_handle(self, field_info: FieldInfo) -> bool:
        """Check if the field is a string type."""
        return field_info.annotation is str

    def check(self, field_info: FieldInfo, registry: BoundednessCheckerRegistry) -> bool:  # noqa: ARG002
        """Check if string field has max_length constraint."""
        return any(isinstance(m, annotated_types.MaxLen) for m in field_info.metadata)


class LiteralChecker(BoundednessChecker):
    """Checker for literal types.

    It checks if the field is a literal type.
    """

    def can_handle(self, field_info: FieldInfo) -> bool:
        """Check if the field is a literal type."""
        return get_origin(field_info.annotation) is Literal

    def check(self, field_info: FieldInfo, registry: BoundednessCheckerRegistry) -> bool:  # noqa: ARG002
        """Check if literal field is properly bounded."""
        return get_origin(field_info.annotation) is Literal


class SequenceChecker(BoundednessChecker):
    """Checker for sequence types with recursive element checking."""

    SEQUENCE_TYPES: ClassVar[set[type]] = {list, tuple, set}

    def can_handle(self, field_info: FieldInfo) -> bool:
        """Check if the field is a sequence type (list, tuple, set)."""
        origin = field_info.annotation if inspect.isclass(field_info.annotation) else get_origin(field_info.annotation)
        return origin in self.SEQUENCE_TYPES

    def check(self, field_info: FieldInfo, registry: BoundednessCheckerRegistry) -> bool:
        """Check if sequence field has max_length constraint and recursively checks elements."""
        # First check if the sequence itself is bounded
        has_max_len = any(isinstance(m, annotated_types.MaxLen) for m in field_info.metadata)
        if not has_max_len:
            return False

        # Then recursively check element types
        args = get_args(field_info.annotation)
        if args:
            element_type = args[0]
            # Only check boundedness for complex types (BoundedModel subclasses)
            # Primitive types in sequences don't need individual bounds
            if isinstance(element_type, type) and issubclass(element_type, BaseModel):
                element_field = FieldInfo(annotation=element_type, default=...)
                if not registry.check_field(element_field):
                    return False

        return True


class BaseModelChecker(BoundednessChecker):
    """Checker for nested BoundedModel types."""

    def can_handle(self, field_info: FieldInfo) -> bool:
        """Check if the field is a BoundedModel type."""
        field_type = field_info.annotation
        return inspect.isclass(field_type) and issubclass(field_type, BaseModel)

    def check(self, field_info: FieldInfo, registry: BoundednessCheckerRegistry) -> bool:
        """Check if the BoundedModel field is properly bounded."""
        field_type = field_info.annotation
        if inspect.isclass(field_type) and issubclass(field_type, BaseModel):
            return registry.check_model(field_type)

        msg = "This line should not be reached: BoundedModelChecker can only handle BaseModel subclasses."
        raise RuntimeError(msg)


class OptionalChecker(BoundednessChecker):
    """Checker for Optional/Union types."""

    def can_handle(self, field_info: FieldInfo) -> bool:
        """Check if the field is an Optional type (Union with None)."""
        origin = get_origin(field_info.annotation)
        # Handle both typing.Union and types.UnionType (Python 3.10+ | syntax)
        return origin is Union or (hasattr(types, "UnionType") and origin is types.UnionType)

    def check(self, field_info: FieldInfo, registry: BoundednessCheckerRegistry) -> bool:
        """Check if Optional/Union field is properly bounded."""
        args = get_args(field_info.annotation)
        non_none_types = [t for t in args if t is not type(None)]

        if len(non_none_types) == 1:
            # This is Optional[T], check T

            # TODO: Should not create `FieldInfo` directly.
            inner_field = FieldInfo(  # type: ignore[call-arg]
                annotation=non_none_types[0],
                default=...,
                metadata=field_info.metadata,
            )
            return registry.check_field(inner_field)

        # For other Union types, all must be bounded
        for t in non_none_types:
            # TODO: Should not create `FieldInfo` directly.
            inner_field = FieldInfo(annotation=t, default=..., metadata=field_info.metadata)  # type: ignore[call-arg]
            if not registry.check_field(inner_field):
                return False
        return True
