---
icon: material/lock
---

# Constant Fields

Sometimes you want models with a mix of sampled parameters and fixed constants. The `allow_constants` parameter enables this.

## Overview

By default, all fields must be bounded. With `allow_constants=True`, unbounded fields with default values are treated as constants:

- They contribute 0 dimensions
- Their default value is used when sampling

## Basic Usage

```python
from pydantic import BaseModel, Field
from bounded_models import FieldHandlerRegistry

class Config(BaseModel):
    name: str = "experiment_1"  # Constant (unbounded with default)
    learning_rate: float = Field(ge=1e-5, le=1e-1)  # Sampled

registry = FieldHandlerRegistry.default()

# Strict mode (default): raises UnboundedFieldError
# registry.model_dimensions(Config)  # Error!

# Lenient mode: constants allowed
registry.model_dimensions(Config, allow_constants=True)  # 1

# Sample uses default for constants
instance = registry.sample_model([0.5], Config, allow_constants=True)
# Config(name="experiment_1", learning_rate=0.00316...)
```

## Using default_factory

Fields with `default_factory` also work as constants:

```python
from pydantic import BaseModel, Field
from bounded_models import FieldHandlerRegistry

class Config(BaseModel):
    tags: list[str] = Field(default_factory=list)
    rate: float = Field(ge=0.0, le=1.0)

registry = FieldHandlerRegistry.default()
instance = registry.sample_model([0.5], Config, allow_constants=True)
# Config(tags=[], rate=0.5)
```

## BoundedModel with Constants

Use `__allow_constants__` class attribute:

```python
from bounded_models import BoundedModel
from pydantic import Field

class StrictModel(BoundedModel):
    # Default: all fields must be bounded
    x: float = Field(ge=0.0, le=1.0)

class LenientModel(BoundedModel):
    __allow_constants__ = True
    
    name: str = "default"  # OK: has default
    x: float = Field(ge=0.0, le=1.0)
```

## Exceptions

### UnboundedFieldError

Raised when `allow_constants=False` and a field is unbounded:

```python
from bounded_models import FieldHandlerRegistry, UnboundedFieldError
from pydantic import BaseModel

class BadModel(BaseModel):
    name: str = "test"  # Unbounded

registry = FieldHandlerRegistry.default()
try:
    registry.model_dimensions(BadModel)  # allow_constants=False by default
except UnboundedFieldError as e:
    print(e)  # "Field 'name' with type 'str' is unbounded..."
```

### MissingDefaultError

Raised when an unbounded field has no default value:

```python
from bounded_models import FieldHandlerRegistry, MissingDefaultError
from pydantic import BaseModel, Field

class BadModel(BaseModel):
    name: str  # Unbounded AND no default!
    rate: float = Field(ge=0.0, le=1.0)

registry = FieldHandlerRegistry.default()
try:
    registry.model_dimensions(BadModel, allow_constants=True)
except MissingDefaultError as e:
    print(e)  # "Field 'name' with type 'str' is unbounded and has no default..."
```

## Behavior Summary

| Field State | `allow_constants=False` | `allow_constants=True` |
|-------------|-------------------------|------------------------|
| Bounded | Sample normally | Sample normally |
| Unbounded + has default | `UnboundedFieldError` | Use default (0 dims) |
| Unbounded + no default | `UnboundedFieldError` | `MissingDefaultError` |
