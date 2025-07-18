# BoundedModel: Validator-Sampler Integration Design

This document proposes a design that integrates Hypothesis and Faker concepts into BoundedModel, ensuring that validation and sampling are dual aspects of the same constraints.

## Core Principle: Validator-Sampler Duality

Every constraint should be both:
1. **Validatable**: Can check if a value satisfies the constraint
2. **Sampleable**: Can generate values that satisfy the constraint

## 1. Basic API Design

### 1.1 Field-Level Constraints with Sampling

```python
from bounded_models import BoundedModel, Field, constraint, sampler
from typing import Annotated
import random

class User(BoundedModel):
    # Simple bounded field with automatic sampling
    age: Annotated[int, Field(ge=0, le=120)]

    # Custom constraint that's also a sampler
    @constraint("age")
    @sampler("age")
    def age_distribution(cls, value=None):
        """Validator when value is provided, sampler when None"""
        if value is not None:
            # Validation mode
            return 0 <= value <= 120 and value != 13  # No 13 (superstition)
        else:
            # Sampling mode
            age = random.randint(0, 120)
            return age if age != 13 else 14
```

### 1.2 Unified Constraint-Sampler Decorators

```python
from bounded_models import constraint_sampler

class Product(BoundedModel):
    sku: str
    price: Annotated[float, Field(gt=0)]

    @constraint_sampler("sku")
    def valid_sku(cls, value=None, draw=None):
        """
        Dual-purpose method:
        - When value is provided: validate
        - When draw is provided: generate
        """
        pattern = r"^[A-Z]{3}-\d{4}$"

        if value is not None:
            # Validation mode
            import re
            return bool(re.match(pattern, value))
        elif draw is not None:
            # Generation mode (Hypothesis-style)
            prefix = draw(st.text(alphabet=string.ascii_uppercase, min_size=3, max_size=3))
            number = draw(st.integers(min_value=1000, max_value=9999))
            return f"{prefix}-{number}"
```

## 2. Strategy-Based Generation (Hypothesis-style)

### 2.1 Built-in Strategy Support

```python
from bounded_models import BoundedModel, Field, strategy
from hypothesis import strategies as st

class Order(BoundedModel):
    # Direct strategy assignment
    order_id: Annotated[str, strategy(st.uuids().map(str))]

    # Combine with Field constraints
    quantity: Annotated[
        int,
        Field(gt=0, le=1000),
        strategy(st.integers(min_value=1, max_value=1000))
    ]

    # Custom strategy with business logic
    @strategy("quantity")
    def quantity_strategy(cls):
        # 80% small orders (1-10), 20% large orders (11-1000)
        return st.one_of(
            st.integers(1, 10).filter(lambda x: x > 0),  # 80% weight
            st.integers(11, 1000),  # 20% weight
        )
```

### 2.2 Composite Strategies

```python
class Address(BoundedModel):
    street: str
    city: str
    country: Literal["US", "CA", "UK"]

    @composite_strategy
    def realistic_address(draw):
        country = draw(st.sampled_from(["US", "CA", "UK"]))
        if country == "US":
            city = draw(st.sampled_from(["New York", "Los Angeles", "Chicago"]))
        elif country == "CA":
            city = draw(st.sampled_from(["Toronto", "Vancouver", "Montreal"]))
        else:
            city = draw(st.sampled_from(["London", "Manchester", "Edinburgh"]))

        street = draw(st.text(min_size=5, max_size=50))
        return cls(street=street, city=city, country=country)
```

## 3. Provider-Based Generation (Faker-style)

### 3.1 Provider Integration

```python
from bounded_models import BoundedModel, provider
from faker import Faker

fake = Faker()

class Customer(BoundedModel):
    # Use Faker providers directly
    name: Annotated[str, provider(fake.name)]
    email: Annotated[str, provider(fake.email)]
    phone: Annotated[str, provider(fake.phone_number)]

    # Custom provider with validation
    @provider("email")
    @validator("email")
    def business_email(cls, value=None):
        if value is not None:
            # Validation: must be corporate email
            return "@" in value and not value.endswith(("gmail.com", "yahoo.com"))
        else:
            # Generation: create corporate email
            name = fake.user_name()
            company = fake.company().replace(" ", "").lower()
            return f"{name}@{company}.com"
```

### 3.2 Bounded Faker Providers

```python
from bounded_models import bounded_provider

class Employee(BoundedModel):
    # Faker provider with bounds
    salary: Annotated[
        float,
        bounded_provider(
            fake.pyfloat,
            min_value=30000,
            max_value=200000,
            right_digits=2
        )
    ]

    department: Annotated[
        str,
        bounded_provider(
            fake.random_element,
            elements=["Engineering", "Sales", "Marketing", "HR"]
        )
    ]
```

## 4. Model-Level Constraints and Sampling

### 4.1 Cross-Field Validation and Sampling

```python
class PricedItem(BoundedModel):
    price: Annotated[float, Field(ge=0, le=1000)]
    tax_rate: Annotated[float, Field(ge=0, le=0.25)]
    total: Annotated[float, Field(ge=0, le=1250)]

    @model_constraint
    def price_tax_total_consistency(self):
        """Validates relationship between fields"""
        expected_total = self.price * (1 + self.tax_rate)
        return abs(self.total - expected_total) < 0.01

    @model_sampler
    def consistent_pricing(cls, draw):
        """Generates consistent field values"""
        price = draw(st.floats(min_value=0, max_value=1000))
        tax_rate = draw(st.floats(min_value=0, max_value=0.25))
        total = price * (1 + tax_rate)
        return {"price": price, "tax_rate": tax_rate, "total": total}
```

### 4.2 Conditional Sampling

```python
class ConditionalModel(BoundedModel):
    user_type: Literal["free", "premium", "enterprise"]
    storage_limit: int

    @field_sampler("storage_limit", depends_on=["user_type"])
    def storage_by_user_type(cls, user_type, draw):
        if user_type == "free":
            return draw(st.integers(min_value=1, max_value=5))
        elif user_type == "premium":
            return draw(st.integers(min_value=10, max_value=100))
        else:  # enterprise
            return draw(st.integers(min_value=100, max_value=10000))

    @validator("storage_limit")
    def validate_storage_limit(cls, v, values):
        user_type = values.get("user_type")
        if user_type == "free" and v > 5:
            raise ValueError("Free users cannot have more than 5GB")
        return v
```

## 5. Sampling Configuration

### 5.1 Sampling Strategies

```python
class DataModel(BoundedModel):
    class SamplingConfig:
        # Global sampling strategy
        strategy = "uniform"  # or "weighted", "edge_cases", "realistic"

        # Field-specific overrides
        field_strategies = {
            "age": "normal_distribution",
            "email": "realistic"
        }

        # Edge case probability
        edge_case_probability = 0.1

        # Custom weights
        field_weights = {
            "status": {"active": 0.7, "inactive": 0.2, "pending": 0.1}
        }
```

### 5.2 Sampling Methods

```python
class BoundedModel:
    @classmethod
    def sample(cls, n=1, strategy="default", **kwargs):
        """Generate samples using configured strategy"""
        pass

    @classmethod
    def sample_valid(cls, n=1, max_attempts=1000):
        """Generate samples that pass all validators"""
        pass

    @classmethod
    def sample_edge_cases(cls, n=1):
        """Generate edge case samples"""
        pass

    @classmethod
    def sample_realistic(cls, n=1, locale="en_US"):
        """Generate realistic samples using Faker providers"""
        pass
```

## 6. Integration with Existing Tools

### 6.1 Hypothesis Integration

```python
from bounded_models import to_hypothesis_strategy

# Automatic strategy generation
user_strategy = to_hypothesis_strategy(User)

@given(user=user_strategy)
def test_user_properties(user):
    assert user.is_valid()
    assert User.sample_space_size() > 0
```

### 6.2 Faker Integration

```python
from bounded_models import to_faker_provider

# Create Faker provider from model
UserProvider = to_faker_provider(User)
fake.add_provider(UserProvider)

# Generate using Faker interface
user = fake.user_model()
```

## 7. Implementation Example

Here's a complete example showing all concepts:

```python
from bounded_models import BoundedModel, Field, constraint_sampler, provider
from typing import Annotated, Literal
from datetime import date, timedelta
from hypothesis import strategies as st
from faker import Faker

fake = Faker()

class User(BoundedModel):
    # Simple bounded fields
    user_id: Annotated[int, Field(ge=1, le=999999)]
    age: Annotated[int, Field(ge=18, le=100)]

    # Faker provider with validation
    email: Annotated[str, provider(fake.email)]

    # Literal type (automatically bounded)
    status: Literal["active", "inactive", "suspended"]

    # Custom constraint-sampler
    username: str

    @constraint_sampler("username")
    def valid_username(cls, value=None, draw=None):
        if value is not None:
            # Validation
            return (
                3 <= len(value) <= 20 and
                value.isalnum() and
                value[0].isalpha()
            )
        else:
            # Sampling
            length = draw(st.integers(min_value=3, max_value=20))
            first = draw(st.text(alphabet=string.ascii_lowercase, min_size=1, max_size=1))
            rest = draw(st.text(
                alphabet=string.ascii_lowercase + string.digits,
                min_size=length-1,
                max_size=length-1
            ))
            return first + rest

    # Model-level constraint
    @model_constraint
    def active_users_have_recent_login(self):
        if self.status == "active":
            return (date.today() - self.last_login).days <= 30
        return True

    class SamplingConfig:
        # Prefer realistic data
        strategy = "realistic"

        # Weight active users more heavily
        field_weights = {
            "status": {"active": 0.7, "inactive": 0.2, "suspended": 0.1}
        }

# Usage
users = User.sample(100)  # Generate 100 valid users
edge_cases = User.sample_edge_cases(10)  # Generate edge cases
all_users = User.enumerate_all()  # If space is small enough
```

## 8. Benefits of This Design

1. **Unified Validation/Generation**: Same logic handles both validation and sampling
2. **Flexibility**: Supports multiple generation strategies (Hypothesis-style, Faker-style, custom)
3. **Composability**: Complex models built from simple constraints
4. **Type Safety**: Full typing support with Pydantic
5. **Extensibility**: Easy to add new constraint types and samplers
6. **Backwards Compatible**: Existing BoundedModel validation still works

This design ensures that every validatable constraint is also sampleable, maintaining the duality principle while providing flexible and powerful data generation capabilities.
