# Hypothesis vs Faker vs BoundedModel: API and Functionality Comparison

## Hypothesis

### Core Concept
Hypothesis is a **property-based testing** library that generates test data based on strategies. It's designed to find edge cases and thoroughly test code properties.

### Key API Components

#### 1. Strategies
Strategies are the core building blocks that describe how to generate data:

```python
from hypothesis import strategies as st

# Basic strategies
st.integers(min_value=0, max_value=100)
st.text(min_size=1, max_size=10)
st.floats(min_value=0.0, max_value=1.0)
st.booleans()
st.none()
st.lists(st.integers(), min_size=0, max_size=10)
st.dictionaries(st.text(), st.integers())
st.tuples(st.integers(), st.text())
st.sets(st.integers())
```

#### 2. Composite Strategies
Build complex data from simpler strategies:

```python
@st.composite
def user_strategy(draw):
    return {
        "name": draw(st.text(min_size=1, max_size=50)),
        "age": draw(st.integers(min_value=0, max_value=120)),
        "email": draw(st.emails())
    }
```

#### 3. Constraints and Filtering
```python
# Filter values
st.integers().filter(lambda x: x % 2 == 0)  # Even numbers only

# Map values
st.integers().map(lambda x: x * 2)

# Constrained data
st.text(alphabet=string.ascii_letters, min_size=5, max_size=10)
```

#### 4. Property Testing
```python
from hypothesis import given

@given(st.integers(min_value=0, max_value=100))
def test_something(value):
    assert 0 <= value <= 100
```

### Key Features
- **Shrinking**: Automatically simplifies failing examples
- **Stateful testing**: Test sequences of operations
- **Database of examples**: Remembers failing cases
- **Deterministic**: Can reproduce failures with seeds
- **Edge case focused**: Tries boundary values, empty cases, etc.

## Faker

### Core Concept
Faker is a **fake data generation** library that produces realistic-looking data for testing, demos, and database seeding.

### Key API Components

#### 1. Basic Usage
```python
from faker import Faker
fake = Faker()

# Generate data
fake.name()          # "John Smith"
fake.email()         # "john@example.com"
fake.address()       # "123 Main St..."
fake.phone_number()  # "+1-555-123-4567"
```

#### 2. Providers
Organized by data type category:

```python
# Person data
fake.first_name()
fake.last_name()
fake.prefix()
fake.suffix()

# Internet data
fake.email()
fake.url()
fake.ipv4()
fake.user_name()

# Date/Time
fake.date()
fake.date_between(start_date='-30y', end_date='today')
fake.date_of_birth(minimum_age=18, maximum_age=90)

# Geographic
fake.country()
fake.city()
fake.latitude()
fake.longitude()
```

#### 3. Localization
```python
# Generate locale-specific data
fake_it = Faker('it_IT')  # Italian
fake_ja = Faker('ja_JP')  # Japanese
fake_de = Faker('de_DE')  # German
```

#### 4. Custom Providers
```python
from faker.providers import BaseProvider

class MyProvider(BaseProvider):
    def custom_id(self):
        return f"ID-{self.random_int(1000, 9999)}"

fake.add_provider(MyProvider)
fake.custom_id()  # "ID-5678"
```

### Key Features
- **Realistic data**: Names, addresses, etc. look real
- **Localized**: Supports many languages/regions
- **Deterministic**: Can seed for reproducibility
- **Extensible**: Easy to add custom providers
- **Domain-specific**: Credit cards, ISBNs, colors, etc.

## BoundedModel Comparison

### Similarities with Hypothesis
1. **Constraint-based generation**: Both use constraints to define valid data
2. **Type awareness**: Both understand Python types
3. **Composability**: Build complex from simple
4. **Deterministic options**: Both can use seeds

### Similarities with Faker
1. **Data generation focus**: Both generate data instances
2. **Extensibility**: Both allow custom types/providers
3. **Practical use cases**: Testing, demos, etc.

### Unique Aspects of BoundedModel

#### 1. Boundedness Focus
```python
# BoundedModel explicitly tracks if generation space is finite
class User(BoundedModel):
    status: Literal["active", "inactive"]  # Bounded: 2 values
    name: str  # Unbounded (even with max_length)
    age: Annotated[int, Field(ge=0, le=120)]  # Bounded: 121 values
```

#### 2. Uniform Sampling Guarantee
```python
# Hypothesis: Biased toward "interesting" values
# Faker: No distribution guarantees
# BoundedModel: True uniform sampling from bounded space
User.sample(n=100)  # Each valid instance has equal probability
```

#### 3. Cardinality Awareness
```python
User.sample_space_size()  # Returns exact number of possible instances
User.enumerate_all()  # Generate all possible instances (if small enough)
```

#### 4. Practical vs Theoretical Boundedness
```python
# String with max_length=100 is theoretically bounded but practically unbounded
# BoundedModel makes this distinction explicit
class Config(BoundedModel):
    class BoundedConfig:
        strategy = BoundednessStrategy.PRACTICAL
        max_practical_cardinality = 10_000
```

### When to Use Each

**Use Hypothesis when:**
- Writing property-based tests
- Need to find edge cases
- Testing invariants and properties
- Want automatic test case shrinking

**Use Faker when:**
- Need realistic-looking data
- Seeding databases
- Creating demos or mockups
- Need locale-specific data

**Use BoundedModel when:**
- Need uniform sampling from finite spaces
- Want to ensure all fields are properly constrained
- Building exhaustive test suites
- Need to know exact cardinality of data space
- Want to distinguish practical from theoretical boundedness

### API Design Insights for BoundedModel

From Hypothesis:
- Strategy composition pattern
- Constraint-based API
- Filter/map transformations
- Clear type annotations

From Faker:
- Provider pattern for extensibility
- Intuitive method names
- Seed-based reproducibility
- Rich set of built-in types

Unique additions:
- Explicit boundedness checking
- Cardinality calculation
- Exhaustive enumeration
- Practical boundedness thresholds
- Integration with Pydantic models
