"""Field override utilities for bounded-models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Any, Self

import annotated_types
from pydantic.fields import FieldInfo

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping


class _UnsetType:
    """Sentinel for unset values in FieldOverride."""

    _instance: _UnsetType | None = None

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "UNSET"

    def __bool__(self) -> bool:
        return False


UNSET = _UnsetType()
"""Sentinel value indicating a field override attribute is not set."""


@dataclass
class FieldOverride:
    """Override configuration for a field during sampling.

    Use this to add bounds to unbounded fields or to set default values
    that make fields behave as constants during sampling.

    Attributes:
        ge: Lower bound (inclusive) for numeric fields.
        le: Upper bound (inclusive) for numeric fields.
        gt: Lower bound (exclusive) for numeric fields.
        lt: Upper bound (exclusive) for numeric fields.
        default: Constant value to use instead of sampling.
        default_factory: Callable that returns a constant value.

    Note:
        `default` and `default_factory` are mutually exclusive.

    """

    ge: float | int | None = None
    le: float | int | None = None
    gt: float | int | None = None
    lt: float | int | None = None
    default: Any = UNSET
    default_factory: Callable[[], Any] | None = None

    def __post_init__(self) -> None:
        """Validate that default and default_factory are not both set."""
        if self.default is not UNSET and self.default_factory is not None:
            msg = "Cannot specify both 'default' and 'default_factory' in FieldOverride"
            raise ValueError(msg)

    def has_default(self) -> bool:
        """Return True if this override specifies a default value or factory."""
        return self.default is not UNSET or self.default_factory is not None

    def get_default(self) -> Any:
        """Return the default value, calling default_factory if needed."""
        if self.default_factory is not None:
            return self.default_factory()
        return self.default


def merge_field_override(field_info: FieldInfo, override: FieldOverride) -> FieldInfo:
    """Create a new FieldInfo with override applied.

    This function creates a modified copy of the field_info with:
    - Additional bound metadata from the override (ge, le, gt, lt)
    - Default value from the override if specified

    Args:
        field_info: The original field information.
        override: The override configuration to apply.

    Returns:
        A new FieldInfo with the override applied.

    """
    # Build new metadata list with override bounds
    new_metadata: list[Any] = list(field_info.metadata)

    if override.ge is not None:
        new_metadata.append(annotated_types.Ge(override.ge))
    if override.le is not None:
        new_metadata.append(annotated_types.Le(override.le))
    if override.gt is not None:
        new_metadata.append(annotated_types.Gt(override.gt))
    if override.lt is not None:
        new_metadata.append(annotated_types.Lt(override.lt))

    # Determine default value
    new_default = field_info.default
    new_default_factory = field_info.default_factory
    if override.default is not UNSET:
        new_default = override.default
        new_default_factory = None
    elif override.default_factory is not None:
        new_default_factory = override.default_factory
        new_default = ...  # PydanticUndefined equivalent

    # Create new FieldInfo using from_annotation to properly set metadata
    # We build an Annotated type with the annotation and metadata
    if new_metadata:
        annotated_type = Annotated[(field_info.annotation, *new_metadata)]  # type: ignore[misc]
        result = FieldInfo.from_annotation(annotated_type)  # ty: ignore[invalid-argument-type]
    else:
        result = FieldInfo(annotation=field_info.annotation)

    # Set default values
    if new_default is not ...:
        result.default = new_default
    if new_default_factory is not None:
        result.default_factory = new_default_factory

    return result


def extract_nested_overrides(
    overrides: Mapping[str, FieldOverride],
    prefix: str,
) -> dict[str, FieldOverride]:
    """Extract overrides for a nested model by stripping the prefix.

    For example, if overrides contains {"inner.value": override} and prefix is "inner",
    this returns {"value": override}.

    Args:
        overrides: The full overrides dictionary.
        prefix: The field name prefix to match and strip.

    Returns:
        A dictionary of overrides for the nested model.

    """
    prefix_dot = f"{prefix}."
    return {key[len(prefix_dot) :]: value for key, value in overrides.items() if key.startswith(prefix_dot)}
