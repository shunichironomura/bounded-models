"""Top-level package for bounded-models."""

from __future__ import annotations

from typing import Any, Protocol, Union, get_args, get_origin

import annotated_types
from pydantic import BaseModel


class FieldChecker(Protocol):
    """Protocol for field type checkers."""

    def __call__(self, field_type: type, metadata: list[Any]) -> bool:
        """Check if a field of the given type is properly bounded."""
        ...


class BoundednessReport:
    """Report on boundedness check results."""

    def __init__(self) -> None:
        """Initialize a boundedness report."""
        self.is_bounded = True
        self.unbounded_fields: dict[str, str] = {}

    def add_unbounded_field(self, field_name: str, field_type: Any, reason: str) -> None:
        """Add an unbounded field to the report."""
        self.is_bounded = False
        self.unbounded_fields[field_name] = f"{field_type} ({reason})"


# Type checker functions
def check_numeric_bounds(field_type: type, metadata: list[Any]) -> bool:
    """Check if numeric types have proper bounds."""
    if field_type not in (int, float):
        return True  # Not applicable

    has_lower = any(isinstance(m, (annotated_types.Ge, annotated_types.Gt)) for m in metadata)
    has_upper = any(isinstance(m, (annotated_types.Le, annotated_types.Lt)) for m in metadata)
    return has_lower and has_upper


def check_string_bounds(field_type: type, metadata: list[Any]) -> bool:
    """Check if string types have proper bounds."""
    if field_type is not str:
        return True  # Not applicable

    return any(isinstance(m, annotated_types.MaxLen) for m in metadata)


def check_sequence_bounds(field_type: type, metadata: list[Any]) -> bool:
    """Check if sequence types have proper bounds."""
    if field_type not in (list, tuple, set):
        return True  # Not applicable

    return any(isinstance(m, annotated_types.MaxLen) for m in metadata)


# Registry of type checkers
TYPE_CHECKERS: list[FieldChecker] = [
    check_numeric_bounds,
    check_string_bounds,
    check_sequence_bounds,
]


def extract_base_type(field_annotation: Any) -> type[Any]:
    """Extract the base type from a potentially complex annotation."""
    field_type = field_annotation
    origin = get_origin(field_type)

    if origin:
        field_type = origin

    # Handle Optional types
    if origin is Union:
        args = get_args(field_annotation)
        # Check if it's Optional (Union with None)
        non_none_types = [t for t in args if t is not type(None)]
        if len(non_none_types) == 1:
            field_type = non_none_types[0]
            origin = get_origin(field_type)
            if origin:
                field_type = origin

    return field_type  # type: ignore[no-any-return]


def is_field_bounded(field_info: Any) -> bool:
    """Check if a single field is properly bounded using registered checkers."""
    field_type = extract_base_type(field_info.annotation)
    metadata = field_info.metadata if hasattr(field_info, "metadata") else []

    # Check if it's a nested BoundedModel
    if isinstance(field_type, type) and issubclass(field_type, BoundedModel):
        return field_type.is_bounded()

    # For generic types (list, tuple, set), also check inner types
    origin = get_origin(field_info.annotation)
    if origin in (list, tuple, set):
        args = get_args(field_info.annotation)
        if args:
            # Check if the inner type is a BoundedModel
            inner_type = args[0]
            if isinstance(inner_type, type) and issubclass(inner_type, BoundedModel) and not inner_type.is_bounded():
                return False

    # Run all registered type checkers
    for checker in TYPE_CHECKERS:
        if not checker(field_type, metadata):
            return False

    # For other types, they must have some constraint
    return bool(metadata) or field_type in (int, float, str, list, tuple, set)


def check_model_bounded(model_class: type[BaseModel]) -> BoundednessReport:
    """Check if all fields in a model are properly bounded."""
    report = BoundednessReport()

    for field_name, field_info in model_class.model_fields.items():
        if not is_field_bounded(field_info):
            field_type = extract_base_type(field_info.annotation)

            # Determine the reason
            reason = "missing constraints"
            if field_type in (int, float):
                reason = "missing lower and/or upper bounds"
            elif field_type is str:
                reason = "missing max_length"
            elif field_type in (list, tuple, set):
                reason = "missing max_length/max_items"

            report.add_unbounded_field(field_name, field_info.annotation, reason)

    return report


def register_type_checker(checker: FieldChecker) -> None:
    """Register a new type checker function."""
    TYPE_CHECKERS.append(checker)


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
        report = check_model_bounded(cls)
        return report.is_bounded

    @classmethod
    def get_unbounded_fields(cls) -> dict[str, str]:
        """Get a dictionary of unbounded fields and their types.

        Returns:
            A dictionary mapping field names to their type descriptions for fields
            that are not properly bounded.

        """
        report = check_model_bounded(cls)
        return report.unbounded_fields
