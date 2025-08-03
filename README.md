# Bounded Models

[![PyPI](https://img.shields.io/pypi/v/bounded-models)](https://pypi.org/project/bounded-models/)
![PyPI - License](https://img.shields.io/pypi/l/bounded-models)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/bounded-models)
[![Test Status](https://github.com/shunichironomura/bounded-models/actions/workflows/ci.yaml/badge.svg)](https://github.com/shunichironomura/bounded-models/actions)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
![PyPI - Downloads](https://img.shields.io/pypi/dm/bounded-models)

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
