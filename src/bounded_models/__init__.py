"""Top-level package for bounded-models."""

from __future__ import annotations

import types
from abc import ABC, abstractmethod
from typing import Union, get_args, get_origin

import annotated_types
from pydantic import BaseModel
from pydantic.fields import FieldInfo


class BoundednessChecker(ABC):
    """Abstract base class for type checkers with recursive support."""

    @abstractmethod
    def can_handle(self, field_info: FieldInfo) -> bool:
        """Check if this checker can handle the given field."""
        raise NotImplementedError

    @abstractmethod
    def check(self, field_info: FieldInfo, registry: TypeCheckerRegistry) -> bool:
        """Check if the field is properly bounded, using registry for recursive checks."""
        raise NotImplementedError


class NumericChecker(BoundednessChecker):
    """Checker for numeric types (int, float)."""

    def can_handle(self, field_info: FieldInfo) -> bool:
        """Check if the field is a numeric type."""
        return field_info.annotation in (int, float)

    def check(self, field_info: FieldInfo, registry: TypeCheckerRegistry) -> bool:  # noqa: ARG002
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

    def check(self, field_info: FieldInfo, registry: TypeCheckerRegistry) -> bool:  # noqa: ARG002
        """Check if string field has max_length constraint."""
        return any(isinstance(m, annotated_types.MaxLen) for m in field_info.metadata)


class SequenceChecker(BoundednessChecker):
    """Checker for sequence types with recursive element checking."""

    def can_handle(self, field_info: FieldInfo) -> bool:
        """Check if the field is a sequence type (list, tuple, set)."""
        origin = get_origin(field_info.annotation)
        return origin in (list, tuple, set)

    def check(self, field_info: FieldInfo, registry: TypeCheckerRegistry) -> bool:
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


class BoundedModelChecker(BoundednessChecker):
    """Checker for nested BoundedModel types."""

    def can_handle(self, field_info: FieldInfo) -> bool:
        """Check if the field is a BoundedModel type."""
        field_type = field_info.annotation
        # Handle both direct types and Optional types
        origin = get_origin(field_type)
        if origin is Union:
            # Don't handle Union types here, let OptionalChecker do it
            return False
        return isinstance(field_type, type) and issubclass(field_type, BaseModel)

    def check(self, field_info: FieldInfo, registry: TypeCheckerRegistry) -> bool:  # noqa: ARG002
        """Check if the BoundedModel field is properly bounded."""
        field_type = field_info.annotation
        if isinstance(field_type, type) and issubclass(field_type, BoundedModel):
            return field_type.is_bounded()
        return True


class OptionalChecker(BoundednessChecker):
    """Checker for Optional/Union types."""

    def can_handle(self, field_info: FieldInfo) -> bool:
        """Check if the field is an Optional type (Union with None)."""
        origin = get_origin(field_info.annotation)
        # Handle both typing.Union and types.UnionType (Python 3.10+ | syntax)
        return origin is Union or (hasattr(types, "UnionType") and origin is types.UnionType)

    def check(self, field_info: FieldInfo, registry: TypeCheckerRegistry) -> bool:
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


class TypeCheckerRegistry:
    """Registry for type checkers with priority ordering."""

    def __init__(self) -> None:
        """Initialize the registry with default checkers."""
        self.checkers: list[BoundednessChecker] = []
        self._initialize_default_checkers()

    def _initialize_default_checkers(self) -> None:
        """Initialize with default checkers in priority order."""
        self.checkers = [
            OptionalChecker(),  # Check Optional/Union first
            BoundedModelChecker(),  # Check nested models
            SequenceChecker(),  # Check sequences (can be recursive)
            NumericChecker(),  # Check numbers
            StringChecker(),  # Check strings
        ]

    def register(self, checker: BoundednessChecker, priority: int = -1) -> None:
        """Register a new type checker at the given priority position."""
        if priority < 0:
            self.checkers.append(checker)
        else:
            self.checkers.insert(priority, checker)

    def check_field(self, field_info: FieldInfo) -> bool:
        """Check if a field is properly bounded using appropriate checker."""
        # Find the first checker that can handle this type
        for checker in self.checkers:
            if checker.can_handle(field_info):
                return checker.check(field_info, self)

        # If no checker can handle it, assume it's bounded
        # (e.g., custom types without specific requirements)
        return True


# Global registry instance
_registry = TypeCheckerRegistry()


def is_field_bounded(field_info: FieldInfo) -> bool:
    """Check if a single field is properly bounded using the type checker registry."""
    return _registry.check_field(field_info)


def is_model_bounded(model_class: type[BaseModel]) -> bool:
    """Check if all fields in a model are properly bounded."""
    return all(is_field_bounded(field_info) for field_info in model_class.model_fields.values())


def register_type_checker(checker: BoundednessChecker, priority: int = -1) -> None:
    """Register a new type checker.

    Args:
        checker: The TypeChecker instance to register
        priority: Position in the checker list (0 = highest priority, -1 = append)

    """
    _registry.register(checker, priority)


class BoundedModel(BaseModel):
    """Base class for bounded models.

    This class can be used to define models with bounded fields.
    It inherits from `pydantic.BaseModel` and can be extended with additional functionality.
    """

    @classmethod
    def is_bounded(cls) -> bool:
        """Check if all fields in the model are properly bounded.

        Returns:
            True if the model is properly bounded according to the rules, False otherwise.

        Rules for bounded fields:
        - float/int: Must have both lower (ge/gt) and upper (le/lt) bounds
        - str: Must have max_length (and optionally min_length)
        - list/tuple/set: Must have max_length/max_items (and optionally min_length/min_items)
        - BoundedModel: Recursively check nested models

        """
        return is_model_bounded(cls)
