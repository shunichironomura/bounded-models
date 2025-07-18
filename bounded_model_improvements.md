# BoundedModel Improvements

This document outlines comprehensive improvements for the BoundedModel implementation, focusing on practical boundedness and uniform sampling capabilities.

## 1. Core Design Philosophy

### 1.1 Practical vs Theoretical Boundedness

- **Problem**: `str` with `max_length=100` is theoretically bounded but practically unbounded (e.g., 256^100 possible values)
- **Solution**: Introduce distinction between theoretical and practical boundedness
- **Implementation**:

  ```python
  class BoundednessStrategy(Enum):
      THEORETICAL = "theoretical"  # Current behavior
      PRACTICAL = "practical"      # New default
      CUSTOM = "custom"           # User-defined rules

  class BoundednessConfig:
      strategy: BoundednessStrategy = BoundednessStrategy.PRACTICAL
      max_practical_cardinality: int = 10_000  # Configurable threshold
      string_charset_size: int = 256  # For cardinality calculations
  ```

### 1.2 Field Cardinality Calculation

- Add methods to calculate the size of the sample space for each field
- Use this to determine practical boundedness
- Example: `str` with `max_length=10` has cardinality 256^10, which exceeds practical limits

## 2. Type System Enhancements

### 2.1 Enhanced String Handling

- **Current**: Any `str` with `max_length` is considered bounded
- **Proposed**:
  - `str` is always considered practically unbounded
  - Only `Literal[...]` or `Enum` strings are bounded
  - Add warning system to suggest alternatives

  ```python
  # Unbounded (even with constraints)
  name: Annotated[str, Field(max_length=50)]

  # Bounded alternatives
  status: Literal["active", "inactive", "pending"]
  country: CountryEnum  # Enum with fixed set of values
  ```

### 2.2 Pattern-Based String Types

- Support common constrained string patterns as bounded:

  ```python
  class BoundedPatterns:
      Email = Annotated[str, EmailStr]  # Still unbounded
      ZipCode = Annotated[str, Field(regex=r"^\d{5}$")]  # Bounded: 10^5 values
      PhoneNumber = Annotated[str, Field(regex=r"^\d{10}$")]  # Bounded: 10^10 values
  ```

### 2.3 Composite Type Handling

- **Current**: `list[str]` with `max_length` is bounded if `str` is bounded
- **Proposed**: Propagate unboundedness through containers

  ```python
  # Unbounded because str is unbounded
  tags: Annotated[list[str], Field(max_length=10)]

  # Bounded because elements are bounded
  priorities: Annotated[list[Literal["low", "medium", "high"]], Field(max_length=5)]
  ```

### 2.4 New Supported Types

- `datetime` with `ge`/`le` constraints (discretized to seconds/days)
- `UUID` (always bounded: 2^128 values)
- `IPv4Address` (bounded: 2^32 values)
- `IPv6Address` (practically unbounded: 2^128 values)
- Custom types implementing `__bounded__` protocol

## 3. Sampling and Generation

### 3.1 Uniform Sampling Implementation

```python
class BoundedModel(BaseModel):
    @classmethod
    def sample(cls, n: int = 1, seed: Optional[int] = None) -> list[Self]:
        """Generate n uniform random samples of the model."""
        pass

    @classmethod
    def sample_space_size(cls) -> int:
        """Calculate total number of possible instances."""
        pass

    @classmethod
    def enumerate_all(cls) -> Iterator[Self]:
        """Generate all possible instances (only for small spaces)."""
        pass
```

### 3.2 Sampling Strategies

```python
class SamplingStrategy(Enum):
    UNIFORM = "uniform"          # True uniform sampling
    WEIGHTED = "weighted"        # User-defined weights
    EXHAUSTIVE = "exhaustive"    # All combinations
    BOUNDARY = "boundary"        # Edge cases only
    SMART = "smart"             # ML-based interesting cases
```

### 3.3 Field-Level Sampling Configuration

```python
class SampledField:
    """Field descriptor for custom sampling behavior."""
    distribution: Distribution
    weights: Optional[dict[Any, float]]
    exclude: Optional[list[Any]]

# Usage
class User(BoundedModel):
    age: Annotated[int, Field(ge=0, le=120), SampledField(
        distribution=Distribution.NORMAL,
        weights={0: 0.1, 120: 0.1}  # Emphasize edge cases
    )]
```

## 4. Validation and Developer Experience

### 4.1 Enhanced Validation Messages

```python
class BoundednessReport:
    def suggest_alternatives(self) -> dict[str, list[str]]:
        """Suggest bounded alternatives for unbounded fields."""
        # Example: "Consider using Literal['option1', 'option2'] instead of str"
        pass

    def complexity_score(self) -> float:
        """Calculate overall model complexity based on cardinality."""
        pass
```

### 4.2 Linting and Warnings

```python
@bounded_model_linter
class User(BoundedModel):
    # Warning: str is practically unbounded. Consider using Literal or Enum
    name: Annotated[str, Field(max_length=50)]

    # Warning: Large cardinality (10^10). Consider reducing bounds
    phone: Annotated[int, Field(ge=1_000_000_000, le=9_999_999_999)]
```

### 4.3 Runtime Validation Options

```python
class BoundedModel(BaseModel):
    class Config:
        validate_boundedness_on_init = True
        max_sample_space = 1_000_000
        warn_on_large_space = True
```

## 5. Configuration and Customization

### 5.1 Global Configuration

```python
from bounded_models import configure

configure(
    strategy=BoundednessStrategy.PRACTICAL,
    max_cardinality=10_000,
    string_handling="strict",  # "strict", "permissive", "custom"
    custom_checkers={
        MyCustomType: my_custom_checker
    }
)
```

### 5.2 Model-Level Overrides

```python
class MyModel(BoundedModel):
    class BoundedConfig:
        strategy = BoundednessStrategy.THEORETICAL
        ignore_fields = ["description"]  # Skip boundedness check
        field_overrides = {
            "name": BoundednessOverride(bounded=True, reason="Small user set")
        }
```

### 5.3 Field-Level Decorators

```python
from bounded_models import bounded_field, unbounded_field

class Product(BoundedModel):
    @bounded_field(reason="Fixed SKU format")
    sku: str

    @unbounded_field(reason="Free-form text")
    description: str
```

## 6. Performance Optimizations

### 6.1 Caching

```python
@lru_cache(maxsize=128)
def is_type_bounded(type_annotation: Type) -> bool:
    """Cache boundedness checks for common types."""
    pass

class BoundedModel(BaseModel):
    _boundedness_cache: ClassVar[Optional[BoundednessReport]] = None
```

### 6.2 Lazy Evaluation

```python
class BoundedModel(BaseModel):
    @classmethod
    def is_bounded_lazy(cls) -> bool:
        """Quick check without full analysis."""
        pass

    @classmethod
    def get_bounded_fields_only(cls) -> set[str]:
        """Return only bounded fields without checking all."""
        pass
```

## 7. Integration Ecosystem

### 7.1 Hypothesis Integration

```python
from hypothesis import strategies as st
from bounded_models import to_hypothesis_strategy

@given(user=to_hypothesis_strategy(User))
def test_user_properties(user: User):
    """Automatic strategy generation for property-based testing."""
    pass
```

### 7.2 Data Generation Libraries

```python
from bounded_models import to_faker_provider, to_mimesis_schema

# Faker integration
fake = Faker()
fake.add_provider(to_faker_provider(User))
user = fake.user()

# Mimesis integration
schema = to_mimesis_schema(User)
```

### 7.3 Schema Export

```python
# JSON Schema with boundedness metadata
schema = User.bounded_json_schema()

# OpenAPI with custom extensions
openapi_schema = User.bounded_openapi_schema()
```

## 8. Developer Tools

### 8.1 CLI Tool

```bash
# Analyze model boundedness
bounded-models check myapp.models.User

# Generate samples
bounded-models sample myapp.models.User --count 100 --output samples.json

# Visualize model complexity
bounded-models visualize myapp.models --output model_graph.png
```

### 8.2 IDE Integration

- Type stubs with bounded type annotations
- VSCode extension for inline boundedness hints
- PyCharm plugin for model visualization

### 8.3 Migration Tools

```python
from bounded_models import migrate_to_bounded

# Automatic migration suggestions
@migrate_to_bounded
class LegacyModel(BaseModel):
    name: str  # Suggests: Literal[...] or add max_length
    age: int   # Suggests: add Field(ge=0, le=150)
```

## 9. Advanced Features

### 9.1 Conditional Boundedness

```python
class Order(BoundedModel):
    status: Literal["pending", "completed", "cancelled"]

    # Bounded only when status is "completed"
    completion_date: Optional[datetime] = Field(
        bounded_when=lambda self: self.status == "completed"
    )
```

### 9.2 Dynamic Bounds

```python
class ConfigurableModel(BoundedModel):
    value: Annotated[int, DynamicBound(
        ge=lambda: get_config("min_value"),
        le=lambda: get_config("max_value")
    )]
```

### 9.3 Sampling Constraints

```python
class ConstrainedSampling(BoundedModel):
    x: Annotated[int, Field(ge=0, le=100)]
    y: Annotated[int, Field(ge=0, le=100)]

    @sampling_constraint
    def sum_constraint(self) -> bool:
        return self.x + self.y <= 100
```

## 10. Best Practices and Patterns

### 10.1 Recommended Patterns

```python
# Use Literal for small string sets
status: Literal["active", "inactive", "pending"]

# Use Enum for larger reusable sets
class Country(str, Enum):
    USA = "USA"
    CAN = "CAN"
    # ...

# Use specific types for common patterns
email: EmailStr  # Still unbounded, but type-safe
user_id: UUID4   # Bounded and type-safe

# Use reasonable numeric bounds
age: Annotated[int, Field(ge=0, le=150)]
percentage: Annotated[float, Field(ge=0.0, le=100.0)]
```

### 10.2 Anti-Patterns to Avoid

```python
# Avoid: Unbounded strings
name: str
description: Annotated[str, Field(max_length=1000)]

# Avoid: Unreasonably large bounds
bignum: Annotated[int, Field(ge=-999999, le=999999)]

# Avoid: Unbounded lists of unbounded types
tags: list[str]
```

## Implementation Priority

1. **Phase 1**: Core practical boundedness (Sections 1-2)
2. **Phase 2**: Basic sampling (Section 3.1)
3. **Phase 3**: Enhanced validation and warnings (Section 4)
4. **Phase 4**: Configuration system (Section 5)
5. **Phase 5**: Advanced features and integrations (Sections 6-9)

This roadmap ensures the most critical improvements are implemented first while maintaining backward compatibility.
