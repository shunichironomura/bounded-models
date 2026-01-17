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

    def field_dimensions(self, field_info: FieldInfo) -> int:
        """Return the number of dimensions for a field."""
        for handler in self.iter_handlers():
            if handler.can_handle(field_info):
                return handler.n_dimensions(field_info, self)
        msg = f"No handler found for field with annotation {field_info.annotation}"
        raise ValueError(msg)

    def model_dimensions(self, model: type[BaseModel]) -> int:
        """Return the number of dimensions for a model."""
        return sum(self.field_dimensions(field_info) for field_info in model.model_fields.values())

    def sample_field(
        self,
        unit_values: Iterable[float],
        field_info: FieldInfo,
    ) -> Any:
        """Sample a value from a field based on the provided unit values."""
        for handler in self.iter_handlers():
            if handler.can_handle(field_info):
                return handler.sample(unit_values, field_info, self)
        msg = f"No handler found for field with annotation {field_info.annotation}"
        raise ValueError(msg)

    def sample_model(
        self,
        unit_values: Iterable[float],
        model: type[BaseModel],
    ) -> BaseModel:
        """Sample a model instance based on the provided unit values."""
        unit_values_iter = iter(unit_values)
        field_values: dict[str, Any] = {}
        for field_name, field_info in model.model_fields.items():
            # Take the next unit values for the field
            unit_values = take(self.field_dimensions(field_info), unit_values_iter)
            # Sample the field value
            field_values[field_name] = self.sample_field(unit_values, field_info)
        return model(
            **field_values,
        )

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
