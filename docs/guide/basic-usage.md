---
icon: material/book-open-variant
---

# Basic Usage

This page covers the fundamental usage patterns of bounded-models.

## Creating a Bounded Model

### Using BoundedModel Base Class

The simplest way to ensure your model is bounded is to inherit from `BoundedModel`:

```python
from bounded_models import BoundedModel
from pydantic import Field

class SearchParams(BoundedModel):
    learning_rate: float = Field(ge=1e-5, le=1e-1)
    batch_size: int = Field(ge=1, le=128)
```

`BoundedModel` validates at class definition time that all fields are properly bounded. If a field is unbounded, a `ValueError` is raised immediately.

### Using Regular BaseModel

You can also use regular Pydantic `BaseModel` and check boundedness manually:

```python
from pydantic import BaseModel, Field
from bounded_models import FieldHandlerRegistry

class Config(BaseModel):
    threshold: float = Field(ge=0.0, le=1.0)
    max_iterations: int = Field(ge=1, le=1000)

registry = FieldHandlerRegistry.default()

# Check if bounded
is_bounded = registry.check_model_boundedness(Config)  # True
```

## Calculating Dimensions

The dimensionality of a model is the number of independent parameters:

```python
from typing import Literal
from bounded_models import FieldHandlerRegistry
from pydantic import BaseModel, Field

class ExperimentConfig(BaseModel):
    algorithm: Literal["sgd", "adam", "rmsprop"]  # 1 dimension
    learning_rate: float = Field(ge=1e-5, le=1e-1)  # 1 dimension
    momentum: float = Field(ge=0.0, le=0.99)  # 1 dimension

registry = FieldHandlerRegistry.default()
dims = registry.model_dimensions(ExperimentConfig)  # 3
```

## Sampling Model Instances

Sample instances by providing values in the unit hypercube `[0, 1]^n`:

```python
from bounded_models import FieldHandlerRegistry
from pydantic import BaseModel, Field

class Params(BaseModel):
    x: float = Field(ge=0.0, le=10.0)
    y: float = Field(ge=-5.0, le=5.0)

registry = FieldHandlerRegistry.default()

# Sample at specific point
instance = registry.sample_model([0.0, 0.5], Params)
# Params(x=0.0, y=0.0)

instance = registry.sample_model([1.0, 1.0], Params)
# Params(x=10.0, y=5.0)

instance = registry.sample_model([0.5, 0.25], Params)
# Params(x=5.0, y=-2.5)
```

## Nested Models

Bounded models can be nested:

```python
from bounded_models import BoundedModel
from pydantic import Field

class Position(BoundedModel):
    x: float = Field(ge=0.0, le=100.0)
    y: float = Field(ge=0.0, le=100.0)

class Agent(BoundedModel):
    position: Position  # 2 dimensions from nested model
    speed: float = Field(ge=0.0, le=10.0)  # 1 dimension

registry = FieldHandlerRegistry.default()
dims = registry.model_dimensions(Agent)  # 3
```

## Integration with Quasi-Random Sequences

bounded-models works well with quasi-random sequences for space-filling designs:

```python
import numpy as np
from scipy.stats import qmc
from bounded_models import FieldHandlerRegistry
from pydantic import BaseModel, Field

class SearchSpace(BaseModel):
    param_a: float = Field(ge=0.0, le=1.0)
    param_b: float = Field(ge=0.0, le=1.0)
    param_c: float = Field(ge=0.0, le=1.0)

registry = FieldHandlerRegistry.default()
dims = registry.model_dimensions(SearchSpace)

# Generate Sobol sequence
sampler = qmc.Sobol(d=dims, scramble=True)
samples = sampler.random(n=10)

# Convert to model instances
instances = [registry.sample_model(list(s), SearchSpace) for s in samples]
```
