---
icon: material/home
---

# Welcome to bounded-models

bounded-models is a Python framework to check if Pydantic models are "bounded" and enable uniform sampling from constrained spaces.

## What is a Bounded Model?

A **bounded model** is a Pydantic model where all fields have defined constraints that create a finite, bounded set of valid values. This enables:

- **Uniform sampling**: Generate random instances uniformly distributed across the valid parameter space
- **Dimensionality calculation**: Determine how many independent parameters define your model
- **Validation**: Ensure your models are properly constrained for sampling

## Quick Example

```python
from typing import Annotated, Literal

from bounded_models import FieldHandlerRegistry
from pydantic import BaseModel, Field

class Config(BaseModel):
    mode: Literal["fast", "slow", "medium"]
    threshold: Annotated[float, Field(ge=0.0, le=1.0)]
    count: Annotated[int, Field(ge=1, le=10)]

registry = FieldHandlerRegistry.default()

# Check if the model is bounded
registry.check_model_boundedness(Config)  # True

# Get the number of dimensions (independent parameters)
registry.model_dimensions(Config)  # 3

# Sample a model instance from unit hypercube [0, 1]^dim
registry.sample_model([0.0, 0.5, 0.9], Config)
# Config(mode='fast', threshold=0.5, count=9)
```

## Supported Field Types

| Type | Description | Example |
|------|-------------|---------|
| **Numeric** | `int`, `float` with both upper and lower bounds | `Field(ge=0, le=10)` |
| **Literal** | Finite set of allowed values | `Literal["a", "b", "c"]` |
| **Enum** | Python Enum types | `class Color(Enum): ...` |
| **Nested Models** | `BaseModel` subclasses | Nested `BoundedModel` |

## Getting Started

<div class="grid cards" markdown>

- :material-download:{ .lg .middle } **Installation**

    ---

    Install bounded-models using pip or uv.

    [:octicons-arrow-right-24: Install](installation.md)

- :material-rocket-launch:{ .lg .middle } **User Guide**

    ---

    Learn how to use bounded-models step by step.

    [:octicons-arrow-right-24: Get started](guide/index.md)

- :material-api:{ .lg .middle } **API Reference**

    ---

    Complete API documentation.

    [:octicons-arrow-right-24: API Reference](api-reference.md)

</div>
