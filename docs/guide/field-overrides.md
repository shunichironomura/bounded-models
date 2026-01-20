---
icon: material/pencil
---

# Field Overrides

Field overrides allow you to modify bounds and defaults at sampling time without changing the model definition. This is useful for:

- Making external (third-party) models bounded
- Sampling only a subset of fields while treating others as constants
- Adjusting bounds dynamically based on runtime requirements

## Overview

Use `FieldOverride` to specify bounds or defaults for fields:

```python
from pydantic import BaseModel
from bounded_models import FieldHandlerRegistry, FieldOverride

class ExternalConfig(BaseModel):
    learning_rate: float  # No bounds
    batch_size: int       # No bounds
    name: str             # No bounds

registry = FieldHandlerRegistry.default()

overrides = {
    "learning_rate": FieldOverride(ge=1e-5, le=1e-1),
    "batch_size": FieldOverride(ge=1, le=128),
    "name": FieldOverride(default="experiment"),
}

dims = registry.model_dimensions(
    ExternalConfig,
    overrides=overrides,
    allow_constants=True,
)  # 2

instance = registry.sample_model(
    [0.5, 0.5],
    ExternalConfig,
    overrides=overrides,
    allow_constants=True,
)
# ExternalConfig(learning_rate=0.05..., batch_size=64, name="experiment")
```

## FieldOverride Options

`FieldOverride` supports the following options:

| Option | Type | Description |
|--------|------|-------------|
| `ge` | `float \| int \| None` | Lower bound (inclusive) |
| `le` | `float \| int \| None` | Upper bound (inclusive) |
| `gt` | `float \| int \| None` | Lower bound (exclusive) |
| `lt` | `float \| int \| None` | Upper bound (exclusive) |
| `default` | `Any` | Constant value to use instead of sampling |
| `default_factory` | `Callable[[], Any] \| None` | Factory function for constant value |

Note: `default` and `default_factory` are mutually exclusive.

## Adding Bounds to Unbounded Fields

Override bounds to make unbounded fields samplable:

```python
from pydantic import BaseModel
from bounded_models import FieldHandlerRegistry, FieldOverride

class ThirdPartyConfig(BaseModel):
    temperature: float
    max_tokens: int

registry = FieldHandlerRegistry.default()

overrides = {
    "temperature": FieldOverride(ge=0.0, le=2.0),
    "max_tokens": FieldOverride(ge=1, le=4096),
}

instance = registry.sample_model(
    [0.5, 0.5],
    ThirdPartyConfig,
    overrides=overrides,
)
# ThirdPartyConfig(temperature=1.0, max_tokens=2048)
```

## Treating Fields as Constants

Use `default` or `default_factory` to treat a field as a constant:

```python
from pydantic import BaseModel, Field
from bounded_models import FieldHandlerRegistry, FieldOverride

class Config(BaseModel):
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    z: float = Field(ge=0.0, le=1.0)

registry = FieldHandlerRegistry.default()

# Only sample x and y, fix z to 0.5
overrides = {"z": FieldOverride(default=0.5)}

dims = registry.model_dimensions(
    Config,
    overrides=overrides,
    allow_constants=True,
)  # 2 (only x and y)

instance = registry.sample_model(
    [0.25, 0.75],
    Config,
    overrides=overrides,
    allow_constants=True,
)
# Config(x=0.25, y=0.75, z=0.5)
```

## Using default_factory

For dynamic default values, use `default_factory`:

```python
from bounded_models import FieldOverride

# Each sample gets a fresh list
overrides = {
    "tags": FieldOverride(default_factory=lambda: ["default"]),
}

# Or generate unique values
import uuid
overrides = {
    "id": FieldOverride(default_factory=lambda: str(uuid.uuid4())),
}
```

## Nested Model Overrides

Use dot notation to override fields in nested models:

```python
from pydantic import BaseModel, Field
from bounded_models import FieldHandlerRegistry, FieldOverride

class Inner(BaseModel):
    value: float  # No bounds

class Outer(BaseModel):
    inner: Inner
    rate: float = Field(ge=0.0, le=1.0)

registry = FieldHandlerRegistry.default()

overrides = {
    "inner.value": FieldOverride(ge=0.0, le=10.0),
}

instance = registry.sample_model(
    [0.5, 0.5],  # inner.value, rate
    Outer,
    overrides=overrides,
)
# Outer(inner=Inner(value=5.0), rate=0.5)
```

### Deeply Nested Fields

Dot notation works for any nesting depth:

```python
from pydantic import BaseModel, Field
from bounded_models import FieldHandlerRegistry, FieldOverride

class Level3(BaseModel):
    value: float

class Level2(BaseModel):
    level3: Level3
    x: float = Field(ge=0.0, le=1.0)

class Level1(BaseModel):
    level2: Level2
    y: float = Field(ge=0.0, le=1.0)

registry = FieldHandlerRegistry.default()

overrides = {
    "level2.level3.value": FieldOverride(ge=0.0, le=100.0),
}

instance = registry.sample_model(
    [0.5, 0.5, 0.5],  # level2.level3.value, level2.x, y
    Level1,
    overrides=overrides,
)
```

### Override Entire Nested Model

You can also override an entire nested model with a default:

```python
overrides = {
    "inner": FieldOverride(default=Inner(value=42.0)),
}

instance = registry.sample_model(
    [0.5],  # Only rate is sampled
    Outer,
    overrides=overrides,
    allow_constants=True,
)
# Outer(inner=Inner(value=42.0), rate=0.5)
```

## Module-Level Functions

The module-level convenience functions also support overrides:

```python
from bounded_models import model_dimensions, FieldOverride
from pydantic import BaseModel

class Config(BaseModel):
    value: float

overrides = {"value": FieldOverride(ge=0.0, le=1.0)}

dims = model_dimensions(Config, overrides=overrides)  # 1
```

## Combining with allow_constants

Overrides work together with `allow_constants`:

- Fields with override defaults are always 0 dimensions
- Fields without overrides follow the `allow_constants` rules

```python
from pydantic import BaseModel
from bounded_models import FieldHandlerRegistry, FieldOverride

class Config(BaseModel):
    a: float  # Unbounded, no default
    b: float = 1.0  # Unbounded, has default
    c: float  # Will be bounded via override

registry = FieldHandlerRegistry.default()

overrides = {
    "a": FieldOverride(default=0.5),  # Constant via override
    "c": FieldOverride(ge=0.0, le=1.0),  # Bounded via override
}

# b is unbounded with default - needs allow_constants=True
dims = registry.model_dimensions(
    Config,
    overrides=overrides,
    allow_constants=True,
)  # 1 (only c is sampled)
```
