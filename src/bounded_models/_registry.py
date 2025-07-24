"""Boundedness checker registry."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bounded_models._checkers import (
    BoundedModelChecker,
    BoundednessChecker,
    NumericChecker,
    OptionalChecker,
    SequenceChecker,
    StringChecker,
)

if TYPE_CHECKING:
    from pydantic import BaseModel
    from pydantic.fields import FieldInfo


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
