---
icon: material/rocket-launch
---

# User Guide

This guide will walk you through using bounded-models to work with bounded Pydantic models.

## What You'll Learn

1. **[Basic Usage](basic-usage.md)** - Core concepts and getting started
2. **[Field Handlers](field-handlers.md)** - Supported field types and custom handlers
3. **[Constant Fields](constant-fields.md)** - Treating unbounded fields as constants

## Core Concepts

### Bounded Models

A **bounded model** is a Pydantic model where every field has constraints that define a finite parameter space. This enables uniform sampling across all valid parameter combinations.

### Field Handler Registry

The `FieldHandlerRegistry` is the central component that:

- Checks if fields/models are bounded
- Calculates dimensionality (number of independent parameters)
- Samples model instances from unit hypercube values

### Unit Hypercube Sampling

bounded-models maps the unit hypercube `[0, 1]^n` to your model's parameter space:

- Each dimension corresponds to one bounded field
- Value `0.0` maps to the lower bound
- Value `1.0` maps to the upper bound
- Values in between are linearly interpolated

This approach integrates well with quasi-random sequences (Sobol, Halton) for space-filling designs.

## Quick Start

```python
from bounded_models import FieldHandlerRegistry, BoundedModel
from pydantic import Field

class MyModel(BoundedModel):
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=-10.0, le=10.0)

registry = FieldHandlerRegistry.default()

# Sample from unit hypercube
instance = registry.sample_model([0.5, 0.75], MyModel)
# MyModel(x=0.5, y=5.0)
```
