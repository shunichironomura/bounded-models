# Bounded Models

> [!WARNING]
> This project is in early development and not ready for use.
> The functionality is not yet complete or incorrectly implemented, and the API may change significantly.

This package provides a framework to check if Pydantic models are "bounded". A bounded model is one where all fields have defined constraints that create a "bounded" set of valid values, enabling uniform sampling from the constrained space.

It also provides a convenient class `BoundedModel`, a subclass of `Pydantic.BaseModel` that automatically checks if the model is bounded when instantiated.

## Supported field types

- **Numeric Types**: `int`, `float` with both upper and lower bounds
- **Literal Types**: `Literal` values
- **BaseModel Types**: Nested `BoundedModel` instances

## Usage

```python
from typing import Annotated, Literal

from bounded_models import FieldHandlerRegistry
from pydantic import BaseModel, Field

class C(BaseModel):
    s: Literal["a", "b", "c"]
    n: Annotated[int, Field(ge=0, le=2)]
    x: Annotated[float, Field(ge=0.2, le=0.8)]

reg = FieldHandlerRegistry.default()

reg.check_model_boundedness(C) # True

reg.model_dimensions(C) # 3

# Sample a model instance from a vector in [0, 1]^dim
reg.sample_model([0.2, 0.3, 0.5], C) # C(s='a', n=0, x=0.5)
```
