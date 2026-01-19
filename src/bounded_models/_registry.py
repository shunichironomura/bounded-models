"""Boundedness handler registry."""

from __future__ import annotations

import heapq
from typing import TYPE_CHECKING, Any

from more_itertools import take

from ._handlers import (
    BaseModelFieldHandler,
    FieldHandler,
    LiteralFieldHandler,
    NumericFieldHandler,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from pydantic import BaseModel
    from pydantic.fields import FieldInfo


class UnboundedFieldError(ValueError):
    """Raised when allow_constants=False and field is unbounded."""

    def __init__(self, field_name: str, annotation: type | None = None) -> None:
        self.field_name = field_name
        self.annotation = annotation
        msg = f"Field '{field_name}' is unbounded"
        if annotation is not None:
            msg += f" (type: {annotation})"
        msg += ". Set allow_constants=True to treat it as a constant (requires a default value)."
        super().__init__(msg)


class MissingDefaultError(ValueError):
    """Raised when unbounded field has no default value (or default_factory)."""

    def __init__(self, field_name: str, annotation: type | None = None) -> None:
        self.field_name = field_name
        self.annotation = annotation
        msg = f"Field '{field_name}' is unbounded and has no default value"
        if annotation is not None:
            msg += f" (type: {annotation})"
        msg += ". Either add bounds or provide a default value."
        super().__init__(msg)


class FieldHandlerRegistry:
    """Registry for field handlers with priority ordering."""

    def __init__(
        self,
        handlers: Iterable[tuple[int, FieldHandler] | FieldHandler] = (),
    ) -> None:
        """Initialize the registry with default handlers."""

        def assign_default_priority(
            handler: tuple[int, FieldHandler] | FieldHandler,
        ) -> tuple[int, FieldHandler]:
            """Assign default priority if not provided."""
            if isinstance(handler, tuple):
                assert len(handler) == 2, "Handler must be a tuple of (priority, handler) or just a handler."
                assert isinstance(handler[0], int), "Handler priority must be an integer."
                assert isinstance(handler[1], FieldHandler), "Handler must be an instance of FieldHandler."
                return handler  # ty: ignore[invalid-return-type] # Checked by the assert statements
            assert isinstance(handler, FieldHandler), "Handler must be an instance of FieldHandler."
            return (0, handler)

        heap = [assign_default_priority(c) for c in handlers]

        # Convert to a heap with counter to maintain order and prevent comparing handlers directly
        heap_with_counter = [(priority, i, handler) for i, (priority, handler) in enumerate(heap)]

        heapq.heapify(heap_with_counter)
        self._handlers: list[tuple[int, int, FieldHandler]] = heap_with_counter  # list of (priority, counter, handler)

    def register(self, handler: FieldHandler, priority: int = 0) -> None:
        """Register a new type handler at the given priority position."""
        heapq.heappush(self._handlers, (priority, len(self._handlers), handler))

    def iter_handlers(self) -> Iterable[FieldHandler]:
        """Iterate over all registered handlers in priority order."""
        heap_copy = self._handlers.copy()
        while heap_copy:
            _, _, handler = heapq.heappop(heap_copy)
            yield handler

    def check_field_boundedness(self, field_info: FieldInfo, *, fail_on_no_handler: bool = True) -> bool:
        """Check if a field is properly bounded using appropriate handler."""
        # Find the first handler that can handle this type
        found_handler = False
        for handler in self.iter_handlers():
            if handler.can_handle(field_info):
                found_handler = True
                result = handler.check_boundedness(field_info, self)
                if not result:
                    # If any handler returns False, exit early
                    return False

        return found_handler or not fail_on_no_handler

    def check_model_boundedness(self, model: type[BaseModel], *, fail_on_no_handler: bool = True) -> bool:
        """Check if all fields in a model are properly bounded."""
        return all(
            self.check_field_boundedness(field_info, fail_on_no_handler=fail_on_no_handler)
            for field_info in model.model_fields.values()
        )

    def _raw_field_dimensions(self, field_info: FieldInfo) -> int:
        """Return the raw number of dimensions for a field (internal use).

        This method returns the dimensions a handler would need, regardless of
        whether the field is bounded. Used by handlers for nested types.

        Args:
            field_info: The field to check.

        Returns:
            Number of unit values the handler would need.

        Raises:
            ValueError: If no handler found for the field type.

        """
        for handler in self.iter_handlers():
            if handler.can_handle(field_info):
                return handler.n_dimensions(field_info, self)
        msg = f"No handler found for field with annotation {field_info.annotation}"
        raise ValueError(msg)

    def _raw_model_dimensions(self, model: type[BaseModel]) -> int:
        """Return the raw total dimensions for a model (internal use).

        This method returns the sum of dimensions for all fields, regardless of
        whether they are bounded. Used by handlers for nested types.

        Args:
            model: The model class to check.

        Returns:
            Total number of unit values needed.

        """
        return sum(self._raw_field_dimensions(field_info) for field_info in model.model_fields.values())

    def field_dimensions(
        self,
        field_info: FieldInfo,
        *,
        allow_constants: bool = False,
        field_name: str | None = None,
    ) -> int:
        """Return the number of dimensions for a field.

        Args:
            field_info: The field to check.
            allow_constants: If True, returns 0 for unbounded fields with defaults.
                           If False, raises UnboundedFieldError for unbounded fields.
            field_name: Optional field name for error messages.

        Returns:
            Number of unit values needed. 0 means the field is a constant.

        Raises:
            UnboundedFieldError: If allow_constants=False and field is unbounded.
            MissingDefaultError: If field is unbounded and has no default value.
            ValueError: If no handler found for the field type.

        """
        _field_name = field_name or "<unknown>"

        for handler in self.iter_handlers():
            if handler.can_handle(field_info):
                if handler.check_boundedness(field_info, self):
                    # Field is bounded: return actual dimensions
                    return handler.n_dimensions(field_info, self)
                # Field is unbounded
                if not allow_constants:
                    raise UnboundedFieldError(_field_name, field_info.annotation)
                # allow_constants=True: check for default value
                if field_info.is_required():
                    raise MissingDefaultError(_field_name, field_info.annotation)
                # Has default: constant field, 0 dimensions
                return 0

        msg = f"No handler found for field with annotation {field_info.annotation}"
        raise ValueError(msg)

    def model_dimensions(self, model: type[BaseModel], *, allow_constants: bool = False) -> int:
        """Return the number of dimensions for a model.

        Args:
            model: The model class to check.
            allow_constants: If True, unbounded fields with defaults contribute 0 dimensions.
                           If False, raises UnboundedFieldError for unbounded fields.

        Returns:
            Total number of unit values needed for sampling.

        Raises:
            UnboundedFieldError: If allow_constants=False and any field is unbounded.
            MissingDefaultError: If any field is unbounded and has no default value.

        """
        return sum(
            self.field_dimensions(field_info, allow_constants=allow_constants, field_name=field_name)
            for field_name, field_info in model.model_fields.items()
        )

    def sample_field(
        self,
        unit_values: Iterable[float],
        field_info: FieldInfo,
        *,
        allow_constants: bool = False,
        field_name: str | None = None,
    ) -> Any:
        """Sample a value from a field based on the provided unit values.

        Args:
            unit_values: Unit values in [0, 1] for sampling.
            field_info: The field to sample.
            allow_constants: If True, uses default value for unbounded fields.
                           If False, raises error for unbounded fields.
            field_name: Optional field name for error messages.

        Returns:
            Sampled value for bounded fields, or default value for constant fields.

        Raises:
            UnboundedFieldError: If allow_constants=False and field is unbounded.
            MissingDefaultError: If field is unbounded and has no default value.
            ValueError: If no handler found for the field type.

        """
        _field_name = field_name or "<unknown>"

        for handler in self.iter_handlers():
            if handler.can_handle(field_info):
                if handler.check_boundedness(field_info, self):
                    # Field is bounded: sample normally
                    return handler.sample(unit_values, field_info, self)
                # Field is unbounded
                if not allow_constants:
                    raise UnboundedFieldError(_field_name, field_info.annotation)
                # allow_constants=True: use default value
                if field_info.is_required():
                    raise MissingDefaultError(_field_name, field_info.annotation)
                # Return default value (or call default_factory)
                if field_info.default_factory is not None:
                    return field_info.default_factory()  # ty: ignore[missing-argument]
                return field_info.default

        msg = f"No handler found for field with annotation {field_info.annotation}"
        raise ValueError(msg)

    def sample_model(
        self,
        unit_values: Iterable[float],
        model: type[BaseModel],
        *,
        allow_constants: bool = False,
    ) -> BaseModel:
        """Sample a model instance based on the provided unit values.

        Args:
            unit_values: Unit values in [0, 1] for sampling bounded fields.
            model: The model class to instantiate.
            allow_constants: If True, uses default values for unbounded fields.
                           If False, raises error for any unbounded field.

        Returns:
            Instantiated model with sampled/default values.

        Raises:
            UnboundedFieldError: If allow_constants=False and any field is unbounded.
            MissingDefaultError: If any unbounded field lacks a default value.

        """
        unit_values_iter = iter(unit_values)
        field_values: dict[str, Any] = {}
        for field_name, field_info in model.model_fields.items():
            # Take the next unit values for the field (0 for constants)
            dims = self.field_dimensions(field_info, allow_constants=allow_constants, field_name=field_name)
            field_unit_values = take(dims, unit_values_iter)
            # Sample the field value (or use default for constants)
            field_values[field_name] = self.sample_field(
                field_unit_values,
                field_info,
                allow_constants=allow_constants,
                field_name=field_name,
            )
        return model(**field_values)

    @classmethod
    def default(cls) -> FieldHandlerRegistry:
        """Get the default registry instance."""
        # TODO: Reconsider the selection of default handlers
        return cls(
            handlers=[
                NumericFieldHandler(),
                LiteralFieldHandler(),
                BaseModelFieldHandler(),
            ],
        )


# Global registry instance
default_registry = FieldHandlerRegistry.default()


def is_field_bounded(field_info: FieldInfo) -> bool:
    """Check if a single field is properly bounded using the field handler registry."""
    return default_registry.check_field_boundedness(field_info)


def is_model_bounded(model_class: type[BaseModel]) -> bool:
    """Check if all fields in a model are properly bounded."""
    return default_registry.check_model_boundedness(model_class)


def field_dimensions(field_info: FieldInfo, *, allow_constants: bool = False) -> int:
    """Return the number of dimensions for a field.

    Args:
        field_info: The field to check.
        allow_constants: If True, returns 0 for unbounded fields with defaults.
                       If False, raises UnboundedFieldError for unbounded fields.

    Returns:
        Number of unit values needed. 0 means the field is a constant.

    """
    return default_registry.field_dimensions(field_info, allow_constants=allow_constants)


def model_dimensions(model_class: type[BaseModel], *, allow_constants: bool = False) -> int:
    """Return the total number of dimensions for a model.

    Args:
        model_class: The model class to check.
        allow_constants: If True, unbounded fields with defaults contribute 0 dimensions.
                       If False, raises UnboundedFieldError for unbounded fields.

    Returns:
        Total number of unit values needed for sampling.

    """
    return default_registry.model_dimensions(model_class, allow_constants=allow_constants)
