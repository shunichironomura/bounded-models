---
icon: material/api
---

# API Reference

## Core Classes

### FieldHandlerRegistry

The central registry for field handlers.

```python
class FieldHandlerRegistry:
    def __init__(self, handlers: Sequence[FieldHandler]) -> None: ...
    
    @classmethod
    def default(cls) -> FieldHandlerRegistry:
        """Create a registry with all built-in handlers."""
    
    def check_field_boundedness(
        self,
        field_info: FieldInfo,
    ) -> bool:
        """Check if a field is bounded."""
    
    def check_model_boundedness(
        self,
        model: type[BaseModel],
    ) -> bool:
        """Check if all fields in a model are bounded."""
    
    def field_dimensions(
        self,
        field_info: FieldInfo,
        *,
        allow_constants: bool = False,
        field_name: str | None = None,
    ) -> int:
        """Get the number of dimensions for a field."""
    
    def model_dimensions(
        self,
        model: type[BaseModel],
        *,
        allow_constants: bool = False,
    ) -> int:
        """Get the total dimensions for a model."""
    
    def sample_field(
        self,
        unit_values: Sequence[float],
        field_info: FieldInfo,
        *,
        allow_constants: bool = False,
        field_name: str | None = None,
    ) -> Any:
        """Sample a field value from unit hypercube values."""
    
    def sample_model(
        self,
        unit_values: Sequence[float],
        model: type[BaseModel],
        *,
        allow_constants: bool = False,
    ) -> BaseModel:
        """Sample a model instance from unit hypercube values."""
```

### BoundedModel

A Pydantic BaseModel subclass that validates boundedness at definition time.

```python
class BoundedModel(BaseModel):
    __allow_constants__: ClassVar[bool] = False
```

**Class Attributes:**

- `__allow_constants__`: If `True`, allows unbounded fields with defaults as constants. Default is `False`.

**Example:**

```python
from bounded_models import BoundedModel
from pydantic import Field

class MyModel(BoundedModel):
    x: float = Field(ge=0.0, le=1.0)
    y: int = Field(ge=0, le=10)
```

## Field Handlers

### NumericFieldHandler

Handles numeric fields (`int`, `float`) with bounds.

```python
class NumericFieldHandler(FieldHandler):
    def supports(self, field_info: FieldInfo) -> bool: ...
    def is_bounded(self, field_info: FieldInfo, registry: FieldHandlerRegistry) -> bool: ...
    def n_dimensions(self, field_info: FieldInfo, registry: FieldHandlerRegistry) -> int: ...
    def sample(self, unit_values: Sequence[float], field_info: FieldInfo, registry: FieldHandlerRegistry) -> int | float: ...
```

### LiteralFieldHandler

Handles `Literal` type fields.

```python
class LiteralFieldHandler(FieldHandler): ...
```

### EnumFieldHandler

Handles `Enum` type fields.

```python
class EnumFieldHandler(FieldHandler): ...
```

### BaseModelFieldHandler

Handles nested `BaseModel` fields.

```python
class BaseModelFieldHandler(FieldHandler): ...
```

## Exceptions

### UnboundedFieldError

Raised when `allow_constants=False` and a field is unbounded.

```python
class UnboundedFieldError(ValueError):
    def __init__(self, field_name: str | None, field_type: type | None) -> None: ...
```

### MissingDefaultError

Raised when an unbounded field has no default value.

```python
class MissingDefaultError(ValueError):
    def __init__(self, field_name: str | None, field_type: type | None) -> None: ...
```

## Module-Level Functions

Convenience functions using the default registry:

```python
def field_dimensions(
    field_info: FieldInfo,
    *,
    allow_constants: bool = False,
) -> int:
    """Get field dimensions using the default registry."""

def model_dimensions(
    model: type[BaseModel],
    *,
    allow_constants: bool = False,
) -> int:
    """Get model dimensions using the default registry."""
```
