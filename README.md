# Bounded Models

> [!WARNING]
> This project is in early development and not ready for use.
> The functionality is not yet complete or incorrectly implemented, and the API may change significantly.

A bounded model is a subclass of `Pydantic.BaseModel` whose domain is restricted to a "bounded" set of values.

Loosely, a model is bounded if you can sample instances "uniformly". Note that the definition of "uniform" is not strict; it does not imply the probability distribution of the samples.

Using `BoundedModel` is useful for sampling model instances "uniformly" from the bounded set.
