"""Boundedness checker registry."""

from __future__ import annotations

import heapq
from typing import TYPE_CHECKING

from ._checkers import (
    BaseModelChecker,
    BoundednessChecker,
    LiteralChecker,
    NumericChecker,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from pydantic import BaseModel
    from pydantic.fields import FieldInfo


class BoundednessCheckerRegistry:
    """Registry for boundedness checkers with priority ordering."""

    def __init__(
        self,
        checkers: Iterable[tuple[int, BoundednessChecker] | BoundednessChecker] = (),
    ) -> None:
        """Initialize the registry with default checkers."""

        def assign_default_priority(
            checker: tuple[int, BoundednessChecker] | BoundednessChecker,
        ) -> tuple[int, BoundednessChecker]:
            """Assign default priority if not provided."""
            if isinstance(checker, tuple):
                assert len(checker) == 2, "Checker must be a tuple of (priority, checker) or just a checker."
                assert isinstance(checker[0], int), "Checker priority must be an integer."
                assert isinstance(checker[1], BoundednessChecker), "Checker must be an instance of BoundednessChecker."
                return checker
            assert isinstance(checker, BoundednessChecker), "Checker must be an instance of BoundednessChecker."
            return (0, checker)

        heap = [assign_default_priority(c) for c in checkers]

        # Convert to a heap with counter to maintain order and prevent comparing checkers directly
        heap_with_counter = [(priority, i, checker) for i, (priority, checker) in enumerate(heap)]

        heapq.heapify(heap_with_counter)
        self._checkers: list[tuple[int, int, BoundednessChecker]] = heap_with_counter

    def register(self, checker: BoundednessChecker, priority: int = 0) -> None:
        """Register a new type checker at the given priority position."""
        heapq.heappush(self._checkers, (priority, len(self._checkers), checker))

    def iter_checkers(self) -> Iterable[BoundednessChecker]:
        """Iterate over all registered checkers in priority order."""
        heap_copy = self._checkers.copy()
        while heap_copy:
            _, _, checker = heapq.heappop(heap_copy)
            yield checker

    def check_field(self, field_info: FieldInfo, *, fail_on_no_checker: bool = True) -> bool:
        """Check if a field is properly bounded using appropriate checker."""
        # Find the first checker that can handle this type
        found_handler = False
        for checker in self.iter_checkers():
            if checker.can_handle(field_info):
                found_handler = True
                result = checker.check(field_info, self)
                if not result:
                    # If any checker returns False, exit early
                    return False

        return found_handler or not fail_on_no_checker

    def check_model(self, model: type[BaseModel], *, fail_on_no_checker: bool = True) -> bool:
        """Check if all fields in a model are properly bounded."""
        return all(
            self.check_field(field_info, fail_on_no_checker=fail_on_no_checker)
            for field_info in model.model_fields.values()
        )

    @classmethod
    def default(cls) -> BoundednessCheckerRegistry:
        """Get the default registry instance."""
        # TODO: Reconsider the selection of default checkers
        return cls(
            checkers=[
                NumericChecker(),
                LiteralChecker(),
                BaseModelChecker(),
            ],
        )


# Global registry instance
default_registry = BoundednessCheckerRegistry.default()


def is_field_bounded(field_info: FieldInfo) -> bool:
    """Check if a single field is properly bounded using the type checker registry."""
    return default_registry.check_field(field_info)


def is_model_bounded(model_class: type[BaseModel]) -> bool:
    """Check if all fields in a model are properly bounded."""
    return default_registry.check_model(model_class)
