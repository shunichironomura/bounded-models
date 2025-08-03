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
