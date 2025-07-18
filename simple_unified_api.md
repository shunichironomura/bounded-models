# BoundedModel: Simple Unified API Design

A clean, simple API that unifies validation and sampling without external dependencies.

## Core Philosophy

Each field defines a **value space** - the set of all valid values. This space is used for:
- **Validation**: Is this value in the space?
- **Sampling**: Pick a value from the space
- **Boundedness**: Is the space finite/practical?

## 1. The Basics: Automatic Sampling from Types

Most fields should "just work" based on their type annotations:

```python
from bounded_models import BoundedModel
from typing import Literal, Annotated
from datetime import date

class User(BoundedModel):
    # Numeric ranges - automatically sample uniformly
    age: Annotated[int, Field(ge=18, le=100)]
    score: Annotated[float, Field(ge=0.0, le=100.0)]

    # Literals/Enums - automatically sample uniformly from choices
    status: Literal["active", "inactive", "pending"]
    role: UserRole  # Enum

    # Dates with bounds
    birth_date: Annotated[date, Field(ge=date(1900, 1, 1), le=date(2010, 1, 1))]

    # Boolean - samples True/False uniformly
    is_verified: bool

# Usage is dead simple
user = User.sample()  # Single sample
users = User.sample(100)  # Multiple samples
```

## 2. Value Spaces: The Core Abstraction

Under the hood, each field has a value space:

```python
from bounded_models import ValueSpace

# Built-in value spaces (created automatically from annotations)
IntRange(min=18, max=100)
FloatRange(min=0.0, max=100.0)
Choice(["active", "inactive", "pending"])
DateRange(start=date(1900, 1, 1), end=date(2010, 1, 1))

# You can access them
User.get_value_space("age")  # IntRange(18, 100)
User.get_value_space("age").cardinality()  # 83
User.get_value_space("age").contains(25)  # True
User.get_value_space("age").sample()  # 42
```

## 3. Customizing Sampling Behavior

### 3.1 Simple Overrides with Field

```python
class Product(BoundedModel):
    # Weighted sampling for non-uniform distributions
    quality: Annotated[
        Literal["low", "medium", "high"],
        Field(sample_weights={"low": 0.1, "medium": 0.6, "high": 0.3})
    ]

    # Custom distribution for numeric fields
    price: Annotated[
        float,
        Field(ge=0.99, le=999.99, sample_distribution="log_normal")
    ]

    # Sampling with specific parameters
    quantity: Annotated[
        int,
        Field(ge=1, le=1000, sample_params={"bias": "low", "peak": 10})
    ]
```

### 3.2 Custom Samplers for Complex Logic

```python
from bounded_models import sampler

class Customer(BoundedModel):
    customer_id: str
    email: str
    age: Annotated[int, Field(ge=18, le=100)]

    @sampler("customer_id")
    def generate_customer_id(self) -> str:
        """Generate customer ID like CUST-2024-00001"""
        year = datetime.now().year
        number = self._random.randint(1, 99999)
        return f"CUST-{year}-{number:05d}"

    @sampler("email")
    def generate_email(self) -> str:
        """Generate realistic email addresses"""
        first_names = ["john", "jane", "bob", "alice", "charlie", "eve"]
        last_names = ["smith", "johnson", "williams", "brown", "jones"]
        domains = ["gmail.com", "yahoo.com", "outlook.com", "company.com"]

        first = self._random.choice(first_names)
        last = self._random.choice(last_names)
        domain = self._random.choice(domains)

        return f"{first}.{last}@{domain}"
```

## 4. Dependent Fields and Model-Level Sampling

### 4.1 Field Dependencies

```python
class Order(BoundedModel):
    product_type: Literal["digital", "physical", "subscription"]
    shipping_required: bool
    delivery_days: Optional[int]

    @sampler("shipping_required", depends_on=["product_type"])
    def generate_shipping_required(self, product_type: str) -> bool:
        """Digital products don't require shipping"""
        return product_type == "physical"

    @sampler("delivery_days", depends_on=["shipping_required"])
    def generate_delivery_days(self, shipping_required: bool) -> Optional[int]:
        """Only set delivery days if shipping is required"""
        if shipping_required:
            return self._random.randint(1, 7)
        return None
```

### 4.2 Model-Level Constraints

```python
from bounded_models import model_sampler

class Transaction(BoundedModel):
    amount: Annotated[float, Field(ge=0.01, le=10000.00)]
    tax_rate: Annotated[float, Field(ge=0.0, le=0.15)]
    total: Annotated[float, Field(ge=0.01, le=11500.00)]

    @model_sampler
    def generate_consistent_transaction(self) -> dict:
        """Ensure total = amount * (1 + tax_rate)"""
        amount = self._random.uniform(0.01, 10000.00)
        tax_rate = self._random.uniform(0.0, 0.15)
        total = amount * (1 + tax_rate)

        return {
            "amount": round(amount, 2),
            "tax_rate": round(tax_rate, 4),
            "total": round(total, 2)
        }
```

## 5. Primitives for Building Complex Samplers

BoundedModel provides simple primitives that can be composed:

```python
class ComplexModel(BoundedModel):
    data: dict

    @sampler("data")
    def generate_data(self) -> dict:
        # Use provided primitives
        return {
            "id": self._random_string(length=8, charset="alphanumeric"),
            "name": self._random_string(min_length=3, max_length=20, charset="alpha"),
            "tags": self._random_list(
                sampler=lambda: self._random_choice(["red", "blue", "green"]),
                min_size=1,
                max_size=5
            ),
            "scores": self._random_dict(
                keys=["math", "science", "english"],
                value_sampler=lambda: self._random_int(0, 100)
            ),
            "active": self._random_bool(true_probability=0.8),
            "created": self._random_datetime(
                start=datetime.now() - timedelta(days=365),
                end=datetime.now()
            )
        }
```

## 6. Patterns and Recipes

### 6.1 String Patterns

```python
class Account(BoundedModel):
    # Simple pattern-based strings
    zipcode: Annotated[str, Field(pattern=r"^\d{5}$")]  # Auto-generates matching strings
    phone: Annotated[str, Field(pattern=r"^\+1-\d{3}-\d{3}-\d{4}$")]

    # Complex patterns with custom sampler
    username: str

    @sampler("username")
    def generate_username(self) -> str:
        """Username: 3-15 chars, alphanumeric, must start with letter"""
        length = self._random.randint(3, 15)
        first = self._random_string(length=1, charset="alpha_lower")
        rest = self._random_string(length=length-1, charset="alphanumeric_lower")
        return first + rest
```

### 6.2 Realistic Data Templates

```python
class Person(BoundedModel):
    full_name: str
    email: str
    bio: str

    # Reusable data templates
    FIRST_NAMES = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
    LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Davis"]
    BIO_TEMPLATES = [
        "{job} with {years} years of experience in {field}",
        "Passionate about {interest1} and {interest2}",
        "{degree} graduate working in {industry}"
    ]

    @sampler("full_name")
    def generate_full_name(self) -> str:
        first = self._random.choice(self.FIRST_NAMES)
        last = self._random.choice(self.LAST_NAMES)
        return f"{first} {last}"

    @sampler("email")
    def generate_email(self) -> str:
        # Derive from full_name if already generated
        if hasattr(self, "full_name"):
            name = self.full_name.lower().replace(" ", ".")
            domain = self._random.choice(["gmail.com", "outlook.com"])
            return f"{name}@{domain}"
        else:
            return self.generate_full_name().lower().replace(" ", ".") + "@example.com"
```

## 7. Advanced Features

### 7.1 Sampling Strategies

```python
class DataPoint(BoundedModel):
    value: Annotated[int, Field(ge=0, le=100)]

    class Config:
        # Global sampling strategy
        sampling_strategy = "edge_biased"  # uniform, edge_biased, center_biased

    # Or per-sample strategy
    samples = DataPoint.sample(
        100,
        strategy="edge_biased",  # Emphasize boundaries (0, 100)
        edge_probability=0.3      # 30% chance of edge values
    )
```

### 7.2 Deterministic Sampling

```python
# Reproducible sampling with seeds
model1 = Model.sample(seed=42)
model2 = Model.sample(seed=42)
assert model1 == model2

# Batch sampling with seed
models = Model.sample(100, seed=42)  # Always generates same 100 models
```

### 7.3 Validation-Aware Sampling

```python
class ValidatedModel(BoundedModel):
    x: int
    y: int

    @validator("y")
    def y_greater_than_x(cls, v, values):
        if "x" in values and v <= values["x"]:
            raise ValueError("y must be greater than x")
        return v

    # Sampler automatically respects validator
    @sampler("y", depends_on=["x"])
    def generate_y(self, x: int) -> int:
        # Sample from valid range considering validator
        return self._random.randint(x + 1, 100)
```

## 8. Complete Example

```python
from bounded_models import BoundedModel, sampler, model_sampler
from typing import Literal, Annotated, Optional
from datetime import datetime, date, timedelta

class User(BoundedModel):
    # Simple fields with automatic sampling
    user_id: Annotated[int, Field(ge=1, le=999999)]
    age: Annotated[int, Field(ge=18, le=100)]
    is_active: bool
    account_type: Literal["free", "pro", "enterprise"]

    # Fields with custom sampling
    username: str
    email: str
    created_at: datetime
    last_login: Optional[datetime]

    # Custom samplers
    @sampler("username")
    def generate_username(self) -> str:
        adjectives = ["happy", "clever", "swift", "bright", "cool"]
        nouns = ["coder", "builder", "creator", "maker", "hacker"]
        number = self._random.randint(10, 99)

        adj = self._random.choice(adjectives)
        noun = self._random.choice(nouns)
        return f"{adj}_{noun}_{number}"

    @sampler("email")
    def generate_email(self) -> str:
        # Use the generated username if available
        username = getattr(self, "username", self.generate_username())
        domain = self._random.choice(["gmail.com", "yahoo.com", "company.io"])
        return f"{username}@{domain}"

    @sampler("created_at")
    def generate_created_at(self) -> datetime:
        # Account created within last 2 years
        days_ago = self._random.randint(0, 730)
        return datetime.now() - timedelta(days=days_ago)

    @sampler("last_login", depends_on=["created_at", "is_active"])
    def generate_last_login(self, created_at: datetime, is_active: bool) -> Optional[datetime]:
        if not is_active:
            return None  # Inactive users haven't logged in

        # Last login between account creation and now
        days_since_creation = (datetime.now() - created_at).days
        if days_since_creation > 0:
            days_ago = self._random.randint(0, min(30, days_since_creation))
            return datetime.now() - timedelta(days=days_ago)
        return created_at

# Usage
user = User.sample()  # Single user
users = User.sample(1000, seed=42)  # 1000 reproducible users

# Still works with validation
try:
    user.age = 150  # Validation error
except ValueError:
    pass

# Check boundedness
assert User.is_bounded()  # True - all fields are bounded
print(User.get_cardinality())  # Total possible unique users
```

## Key Benefits

1. **Simple**: Most cases work automatically from type annotations
2. **Flexible**: Easy to customize with decorators when needed
3. **Unified**: Same constraints for validation and sampling
4. **No Dependencies**: No tight coupling to external libraries
5. **Composable**: Build complex samplers from simple primitives
6. **Type Safe**: Full typing support with Pydantic

This design provides the power of Hypothesis and Faker through a simple, unified API that feels natural in the BoundedModel context.
