# Bounded Models

[![PyPI](https://img.shields.io/pypi/v/bounded-models)](https://pypi.org/project/bounded-models/)
![PyPI - License](https://img.shields.io/pypi/l/bounded-models)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/bounded-models)
[![Test Status](https://github.com/shunichironomura/bounded-models/actions/workflows/ci.yaml/badge.svg)](https://github.com/shunichironomura/bounded-models/actions)
[![Documentation](https://img.shields.io/badge/docs-zensical-blue)](https://shunichironomura.github.io/bounded-models/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

> [!WARNING]
> This project is in early development. The API may change significantly.

A framework to check if Pydantic models are "bounded" and enable uniform sampling from constrained spaces.

## Installation

```bash
pip install bounded-models
# or
uv add bounded-models
```

## Quick Start

```python
from typing import Literal
from bounded_models import FieldHandlerRegistry
from pydantic import BaseModel, Field

class Config(BaseModel):
    mode: Literal["fast", "slow"]
    threshold: float = Field(ge=0.0, le=1.0)
    count: int = Field(ge=1, le=10)

registry = FieldHandlerRegistry.default()

registry.check_model_boundedness(Config)  # True
registry.model_dimensions(Config)  # 3

# Sample from unit hypercube [0, 1]^dim
registry.sample_model([0.5, 0.5, 0.5], Config)
# Config(mode='slow', threshold=0.5, count=5)
```

## Supported Field Types

| Type | Example |
|------|---------|
| Numeric (`int`, `float`) | `Field(ge=0, le=10)` |
| `Literal` | `Literal["a", "b", "c"]` |
| `Enum` | `class Color(Enum): ...` |
| Nested `BaseModel` | `BoundedModel` subclasses |

## Documentation

For detailed usage, see the [documentation](https://shunichironomura.github.io/bounded-models/).

## License

MIT
