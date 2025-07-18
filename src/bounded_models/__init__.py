"""Top-level package for bounded-models."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, Union, get_args, get_origin

import annotated_types
from pydantic import BaseModel

if TYPE_CHECKING:
    from pydantic.fields import FieldInfo


class FieldChecker(Protocol):
    """Protocol for field type checkers."""

    def __call__(self, field_info: FieldInfo) -> bool:
        """Check if a field of the given type is properly bounded."""
        ...


# Type checker functions
def check_numeric_bounds(field_info: FieldInfo) -> bool:
    """Check if numeric types have proper bounds."""
    if field_info.annotation not in (int, float):
        return True  # Not applicable

    has_lower = any(isinstance(m, (annotated_types.Ge, annotated_types.Gt)) for m in field_info.metadata)
    has_upper = any(isinstance(m, (annotated_types.Le, annotated_types.Lt)) for m in field_info.metadata)
    return has_lower and has_upper


def check_string_bounds(field_info: FieldInfo) -> bool:
    """Check if string types have proper bounds."""
    if field_info.annotation is not str:
        return True  # Not applicable

    return any(isinstance(m, annotated_types.MaxLen) for m in field_info.metadata)


def check_sequence_bounds(field_info: FieldInfo) -> bool:
    """Check if sequence types have proper bounds."""
    if field_info.annotation not in (list, tuple, set):
        return True  # Not applicable

    return any(isinstance(m, annotated_types.MaxLen) for m in field_info.metadata)


# Registry of type checkers
TYPE_CHECKERS: dict[str, FieldChecker] = {
    "numeric": check_numeric_bounds,
    "string": check_string_bounds,
    "sequence": check_sequence_bounds,
}


# def extract_base_type(field_annotation: type[Any] | None) -> type[Any]:
#     """Extract the base type from a potentially complex annotation.

#     Example:
#         - For `Optional[int]`, it returns `int`.
#         - For `list[str]`, it returns `str`.
#         - For `Union[int, None]`, it returns `int`.
#         - For `Union[str, None]`, it returns `str`.
#         - For `int`, it returns `int`.

#     """
#     field_type = field_annotation
#     origin = get_origin(field_type)

#     if origin:
#         field_type = origin

#     # Handle Optional types
#     if origin is Union:
#         args = get_args(field_annotation)
#         # Check if it's Optional (Union with None)
#         non_none_types = [t for t in args if t is not type(None)]
#         if len(non_none_types) == 1:
#             field_type = non_none_types[0]
#             origin = get_origin(field_type)
#             if origin:
#                 field_type = origin

#     return field_type


def is_field_bounded(field_info: FieldInfo) -> bool:
    """Check if a single field is properly bounded using registered checkers."""
    # field_type = extract_base_type(field_info.annotation)
    # metadata = field_info.metadata if hasattr(field_info, "metadata") else []

    # # Check if it's a nested BoundedModel
    # if isinstance(field_type, type) and issubclass(field_type, BoundedModel):
    #     return is_model_bounded(field_type)

    # # For generic types (list, tuple, set), also check inner types
    # origin = get_origin(field_info.annotation)
    # if origin in (list, tuple, set):
    #     args = get_args(field_info.annotation)
    #     if args:
    #         # Check if the inner type is a BoundedModel
    #         inner_type = args[0]
    #         if (
    #             isinstance(inner_type, type)
    #             and issubclass(inner_type, BoundedModel)
    #             and not is_model_bounded(inner_type)
    #         ):
    #             return False

    # Run all registered type checkers
    return all(checker(field_info) for checker in TYPE_CHECKERS.values())


def is_model_bounded(model_class: type[BaseModel]) -> bool:
    """Check if all fields in a model are properly bounded."""
    return all(is_field_bounded(field_info) for field_info in model_class.model_fields.values())


def register_type_checker(name: str, checker: FieldChecker) -> None:
    """Register a new type checker function."""
    if name in TYPE_CHECKERS:
        msg = f"Type checker '{name}' is already registered."
        raise ValueError(msg)
    TYPE_CHECKERS[name] = checker


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
