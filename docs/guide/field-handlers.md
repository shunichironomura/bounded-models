---
icon: material/cog
---

# Field Handlers

Field handlers determine how different field types are checked for boundedness and sampled.

## Built-in Handlers

### NumericFieldHandler

Handles `int` and `float` fields with `ge`/`le` or `gt`/`lt` constraints.

```python
from pydantic import BaseModel, Field

class NumericExample(BaseModel):
    # Both bounds required for boundedness
    temperature: float = Field(ge=-40.0, le=50.0)
    count: int = Field(ge=0, le=100)
    
    # These are NOT bounded (missing bounds)
    # unbounded_float: float = Field(ge=0.0)  # Missing upper bound
    # unbounded_int: int  # No constraints
```

### LiteralFieldHandler

Handles `Literal` types with a finite set of values.

```python
from typing import Literal
from pydantic import BaseModel

class LiteralExample(BaseModel):
    mode: Literal["train", "eval", "test"]
    priority: Literal[1, 2, 3, 4, 5]
```

Sampling maps the unit interval uniformly across literal values.

### EnumFieldHandler

Handles Python `Enum` types.

```python
from enum import Enum
from pydantic import BaseModel

class Color(Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"

class EnumExample(BaseModel):
    color: Color
```

### BaseModelFieldHandler

Handles nested `BaseModel` subclasses recursively.

```python
from pydantic import BaseModel, Field

class Inner(BaseModel):
    x: float = Field(ge=0.0, le=1.0)

class Outer(BaseModel):
    inner: Inner
    y: float = Field(ge=0.0, le=1.0)
```

## Default Registry

The default registry includes all built-in handlers:

```python
from bounded_models import FieldHandlerRegistry

registry = FieldHandlerRegistry.default()
# Includes: NumericFieldHandler, LiteralFieldHandler,
#           EnumFieldHandler, BaseModelFieldHandler
```

## Custom Registry

Create a registry with specific handlers:

```python
from bounded_models import (
    FieldHandlerRegistry,
    NumericFieldHandler,
    LiteralFieldHandler,
)

# Only numeric and literal handlers
registry = FieldHandlerRegistry(
    handlers=[
        NumericFieldHandler(),
        LiteralFieldHandler(),
    ]
)
```

## Handler Priority

Handlers are checked in order. The first handler that returns `True` for `supports()` is used. Place more specific handlers before general ones.
