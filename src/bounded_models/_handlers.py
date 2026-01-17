"""Field handlers."""

from __future__ import annotations

import inspect
import math
import types
from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar, Literal, Union, get_args, get_origin

import annotated_types
from pydantic import BaseModel
from pydantic.fields import FieldInfo

if TYPE_CHECKING:
    from collections.abc import Iterable

    from ._registry import FieldHandlerRegistry


class FieldHandler[T = Any](ABC):
    """Abstract base class for field handlers with recursive support."""

    @abstractmethod
    def can_handle(self, field_info: FieldInfo) -> bool:
        """Check if this handler can handle the given field."""
        raise NotImplementedError

    @abstractmethod
    def check_boundedness(self, field_info: FieldInfo, registry: FieldHandlerRegistry) -> bool:
        """Check if the field is properly bounded, using registry for recursive checks."""
        raise NotImplementedError

    @abstractmethod
    def n_dimensions(self, field_info: FieldInfo, registry: FieldHandlerRegistry) -> int:
        """Return the number of dimensions for the field."""
        raise NotImplementedError

    @abstractmethod
    def sample(self, unit_values: Iterable[float], field_info: FieldInfo, registry: FieldHandlerRegistry) -> T:
        """Sample a value from the field based on the provided unit values."""
        raise NotImplementedError


class NumericFieldHandler(FieldHandler[int | float]):
    """Checker for numeric types (int, float)."""

    def can_handle(self, field_info: FieldInfo) -> bool:
        """Check if the field is a numeric type."""
        return field_info.annotation in (int, float)

    def check_boundedness(self, field_info: FieldInfo, registry: FieldHandlerRegistry) -> bool:  # noqa: ARG002
        """Check if numeric field has both lower and upper bounds."""
        has_lower = any(isinstance(m, (annotated_types.Ge, annotated_types.Gt)) for m in field_info.metadata)
        has_upper = any(isinstance(m, (annotated_types.Le, annotated_types.Lt)) for m in field_info.metadata)
        return has_lower and has_upper

    def n_dimensions(self, field_info: FieldInfo, registry: FieldHandlerRegistry) -> int:  # noqa: ARG002
        """Return the number of dimensions for numeric fields."""
        return 1

    def sample(
        self,
        unit_values: Iterable[float],
        field_info: FieldInfo,
        registry: FieldHandlerRegistry,  # noqa: ARG002
    ) -> int | float:
        """Sample a numeric value based on the provided unit values."""
        lower_bound = next(m.ge for m in field_info.metadata if isinstance(m, annotated_types.Ge))
        assert isinstance(lower_bound, (int, float)), "Lower bound must be numeric."
        upper_bound = next(m.le for m in field_info.metadata if isinstance(m, annotated_types.Le))
        assert isinstance(upper_bound, (int, float)), "Upper bound must be numeric."

        (unit_value,) = unit_values  # unit_values should be a single float in [0, 1]
        assert 0.0 <= unit_value <= 1.0, "Unit value must be in [0, 1]."
        if field_info.annotation is int:
            lower_bound = math.ceil(lower_bound)
            upper_bound = math.floor(upper_bound)
            n_options = upper_bound - lower_bound + 1
            # Ensure we don't go out of bounds even if unit_value is 1.0
            selected_index = min(int(unit_value * n_options), n_options - 1)
            return lower_bound + selected_index
        return lower_bound + (upper_bound - lower_bound) * unit_value


class StringFieldHandler(FieldHandler[str]):
    """Checker for string types.

    It checks for max_length constraint.
    """

    def can_handle(self, field_info: FieldInfo) -> bool:
        """Check if the field is a string type."""
        return field_info.annotation is str

    def check_boundedness(self, field_info: FieldInfo, registry: FieldHandlerRegistry) -> bool:  # noqa: ARG002
        """Check if string field has max_length constraint."""
        return any(isinstance(m, annotated_types.MaxLen) for m in field_info.metadata)

    def n_dimensions(self, field_info: FieldInfo, registry: FieldHandlerRegistry) -> int:  # noqa: ARG002
        """Return the number of dimensions for string fields."""
        return 1

    def sample(self, unit_values: Iterable[float], field_info: FieldInfo, registry: FieldHandlerRegistry) -> str:
        raise NotImplementedError


class LiteralFieldHandler(FieldHandler[Any]):
    """Checker for literal types.

    It checks if the field is a literal type.
    """

    def can_handle(self, field_info: FieldInfo) -> bool:
        """Check if the field is a literal type."""
        return get_origin(field_info.annotation) is Literal

    def check_boundedness(self, field_info: FieldInfo, registry: FieldHandlerRegistry) -> bool:  # noqa: ARG002
        """Check if literal field is properly bounded."""
        return get_origin(field_info.annotation) is Literal

    def n_dimensions(self, field_info: FieldInfo, registry: FieldHandlerRegistry) -> int:  # noqa: ARG002
        """Return the number of dimensions for literal fields."""
        return 1

    def sample(self, unit_values: Iterable[float], field_info: FieldInfo, registry: FieldHandlerRegistry) -> Any:  # noqa: ARG002
        """Sample a value from the literal field based on the provided unit values."""
        # Get all possible literal values
        literal_values = get_args(field_info.annotation)
        if not literal_values:
            msg = "Literal field must have at least one value."
            raise ValueError(msg)

        # Convert unit_values to an index
        (unit_value,) = unit_values
        assert 0.0 <= unit_value <= 1.0, "Unit value must be in [0, 1]."
        index = int(unit_value * len(literal_values)) % len(literal_values)
        return literal_values[index]


class EnumFieldHandler(FieldHandler[Enum]):
    """Checker for enum types.

    Enum fields are inherently bounded since they have a finite set of members.
    """

    def can_handle(self, field_info: FieldInfo) -> bool:
        """Check if the field is an Enum type."""
        return inspect.isclass(field_info.annotation) and issubclass(field_info.annotation, Enum)

    def check_boundedness(self, field_info: FieldInfo, registry: FieldHandlerRegistry) -> bool:  # noqa: ARG002
        """Check if enum field is properly bounded.

        Enum fields are always bounded since they have a finite set of members.
        """
        return inspect.isclass(field_info.annotation) and issubclass(field_info.annotation, Enum)

    def n_dimensions(self, field_info: FieldInfo, registry: FieldHandlerRegistry) -> int:  # noqa: ARG002
        """Return the number of dimensions for enum fields."""
        return 1

    def sample(self, unit_values: Iterable[float], field_info: FieldInfo, registry: FieldHandlerRegistry) -> Enum:  # noqa: ARG002
        """Sample a value from the enum field based on the provided unit values."""
        enum_class = field_info.annotation
        assert inspect.isclass(enum_class), "Annotation must be a class."
        assert issubclass(enum_class, Enum), "Annotation must be an Enum type."
        members = list(enum_class)
        if not members:
            msg = "Enum field must have at least one member."
            raise ValueError(msg)

        # Convert unit_values to an index
        (unit_value,) = unit_values
        assert 0.0 <= unit_value <= 1.0, "Unit value must be in [0, 1]."
        # Ensure we don't go out of bounds even if unit_value is 1.0
        index = min(int(unit_value * len(members)), len(members) - 1)
        return members[index]


class SequenceFieldHandler(FieldHandler[Any]):
    """Checker for sequence types with recursive element checking."""

    SEQUENCE_TYPES: ClassVar[set[type]] = {list, tuple, set}

    def can_handle(self, field_info: FieldInfo) -> bool:
        """Check if the field is a sequence type (list, tuple, set)."""
        origin = field_info.annotation if inspect.isclass(field_info.annotation) else get_origin(field_info.annotation)
        return origin in self.SEQUENCE_TYPES

    def check_boundedness(self, field_info: FieldInfo, registry: FieldHandlerRegistry) -> bool:
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
                if not registry.check_field_boundedness(element_field):
                    return False

        return True

    def n_dimensions(self, field_info: FieldInfo, registry: FieldHandlerRegistry) -> int:
        """Return the number of dimensions for sequence fields."""
        raise NotImplementedError

    def sample(self, unit_values: Iterable[float], field_info: FieldInfo, registry: FieldHandlerRegistry) -> Any:
        """Sample a value from the sequence field based on the provided unit values."""
        raise NotImplementedError


class BaseModelFieldHandler(FieldHandler[BaseModel]):
    """Checker for nested BoundedModel types."""

    def can_handle(self, field_info: FieldInfo) -> bool:
        """Check if the field is a BoundedModel type."""
        field_type = field_info.annotation
        return inspect.isclass(field_type) and issubclass(field_type, BaseModel)

    def check_boundedness(self, field_info: FieldInfo, registry: FieldHandlerRegistry) -> bool:
        """Check if the BoundedModel field is properly bounded."""
        field_type = field_info.annotation
        if inspect.isclass(field_type) and issubclass(field_type, BaseModel):
            return registry.check_model_boundedness(field_type)

        msg = "This line should not be reached: BoundedModelChecker can only handle BaseModel subclasses."
        raise RuntimeError(msg)

    def n_dimensions(self, field_info: FieldInfo, registry: FieldHandlerRegistry) -> int:
        """Return the number of dimensions for BoundedModel fields."""
        field_type = field_info.annotation
        if inspect.isclass(field_type) and issubclass(field_type, BaseModel):
            return registry.model_dimensions(field_type)
        msg = "This line should not be reached: BoundedModelChecker can only handle BaseModel subclasses."
        raise RuntimeError(msg)

    def sample(self, unit_values: Iterable[float], field_info: FieldInfo, registry: FieldHandlerRegistry) -> BaseModel:
        """Sample a BoundedModel instance based on the provided unit values."""
        field_type = field_info.annotation
        if inspect.isclass(field_type) and issubclass(field_type, BaseModel):
            return registry.sample_model(unit_values, field_type)

        msg = "This line should not be reached: BoundedModelChecker can only handle BaseModel subclasses."
        raise RuntimeError(msg)


class OptionalFieldHandler(FieldHandler[Any | None]):
    """Checker for Optional/Union types."""

    def can_handle(self, field_info: FieldInfo) -> bool:
        """Check if the field is an Optional type (Union with None)."""
        origin = get_origin(field_info.annotation)
        # Handle both typing.Union and types.UnionType (Python 3.10+ | syntax)
        return origin is Union or (hasattr(types, "UnionType") and origin is types.UnionType)

    def check_boundedness(self, field_info: FieldInfo, registry: FieldHandlerRegistry) -> bool:
        """Check if Optional/Union field is properly bounded."""
        args = get_args(field_info.annotation)
        non_none_types = [t for t in args if t is not type(None)]

        if len(non_none_types) == 1:
            # This is Optional[T], check T

            # TODO: Should not create `FieldInfo` directly.
            inner_field = FieldInfo(
                annotation=non_none_types[0],
                default=...,
                metadata=field_info.metadata,
            )
            return registry.check_field_boundedness(inner_field)

        # For other Union types, all must be bounded
        for t in non_none_types:
            # TODO: Should not create `FieldInfo` directly.
            inner_field = FieldInfo(annotation=t, default=..., metadata=field_info.metadata)
            if not registry.check_field_boundedness(inner_field):
                return False
        return True

    def n_dimensions(self, field_info: FieldInfo, registry: FieldHandlerRegistry) -> int:
        raise NotImplementedError

    def sample(self, unit_values: Iterable[float], field_info: FieldInfo, registry: FieldHandlerRegistry) -> Any | None:
        """Sample a value from the Optional/Union field based on the provided unit values."""
        raise NotImplementedError
