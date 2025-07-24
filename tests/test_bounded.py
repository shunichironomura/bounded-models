from typing import Annotated, Any

import annotated_types
from pydantic import Field

from bounded_models import BoundedModel
from bounded_models._checkers import BoundednessChecker
from bounded_models._registry import TypeCheckerRegistry, register_type_checker


def test_no_fields() -> None:
    class ModelWithNoFields(BoundedModel):
        """A simple bounded model with no fields."""

    assert ModelWithNoFields.is_bounded()


def test_numeric_bounds() -> None:
    class ProperlyBoundedNumeric(BoundedModel):
        bounded_float: Annotated[list[Annotated[float, Field(ge=0.0, le=1.0)]], Field(max_length=10)]
        bounded_int: int = Field(gt=0, lt=100)
        bounded_float_mixed: float = Field(ge=0.0, lt=1.0)

    assert ProperlyBoundedNumeric.is_bounded()

    class UnboundedNumeric(BoundedModel):
        unbounded_float: float
        only_lower_float: float = Field(ge=0.0)
        only_upper_int: int = Field(le=100)

    assert not UnboundedNumeric.is_bounded()


def test_string_bounds() -> None:
    class ProperlyBoundedString(BoundedModel):
        bounded_str: str = Field(max_length=50)
        bounded_str_with_min: str = Field(min_length=1, max_length=100)

    assert ProperlyBoundedString.is_bounded()

    class UnboundedString(BoundedModel):
        unbounded_str: str
        only_min_length: str = Field(min_length=1)

    assert not UnboundedString.is_bounded()


def test_sequence_bounds() -> None:
    class ProperlyBoundedSequence(BoundedModel):
        bounded_list: Annotated[list[str], Field(max_length=10)]
        bounded_tuple: tuple[int, ...] = Field(max_length=5)
        bounded_set: set[float] = Field(max_length=20)

    assert ProperlyBoundedSequence.is_bounded()

    class UnboundedSequence(BoundedModel):
        unbounded_list: list[int]
        unbounded_tuple: tuple[str, ...]
        unbounded_set: set[float]

    assert not UnboundedSequence.is_bounded()


def test_optional_fields() -> None:
    class ModelWithOptionals(BoundedModel):
        optional_bounded_float: float | None = Field(ge=0.0, le=1.0)
        optional_bounded_str: str | None = Field(max_length=50)
        optional_unbounded_int: int | None = None

    assert not ModelWithOptionals.is_bounded()


def test_nested_bounded_models() -> None:
    class InnerBounded(BoundedModel):
        value: float = Field(ge=0.0, le=1.0)

    class InnerUnbounded(BoundedModel):
        value: float

    class OuterWithBoundedInner(BoundedModel):
        inner: InnerBounded
        count: int = Field(ge=0, le=100)

    class OuterWithUnboundedInner(BoundedModel):
        inner: InnerUnbounded
        count: int = Field(ge=0, le=100)

    assert InnerBounded.is_bounded()
    assert not InnerUnbounded.is_bounded()
    assert OuterWithBoundedInner.is_bounded()
    assert not OuterWithUnboundedInner.is_bounded()


def test_mixed_bounded_unbounded() -> None:
    class MixedModel(BoundedModel):
        bounded_float: float = Field(ge=0.0, le=1.0)
        unbounded_float: float
        bounded_str: str = Field(max_length=50)
        unbounded_list: list[int]
        bounded_list: list[str] = Field(max_length=10)

    assert not MixedModel.is_bounded()


def test_custom_type_checker() -> None:
    # Test registering a custom checker for dict types
    from typing import get_origin

    class DictChecker(BoundednessChecker):
        def can_handle(self, field_info: Any) -> bool:
            return get_origin(field_info.annotation) is dict or field_info.annotation is dict

        def check(self, field_info: Any, registry: TypeCheckerRegistry) -> bool:
            # Check for max_length constraint
            return any(isinstance(m, annotated_types.MaxLen) for m in field_info.metadata)

    register_type_checker(DictChecker())

    class ModelWithDict(BoundedModel):
        bounded_dict: dict[str, int] = Field(max_length=10)
        unbounded_dict: dict[str, str]

    assert not ModelWithDict.is_bounded()


def test_complex_nested_structure() -> None:
    class Address(BoundedModel):
        street: str = Field(max_length=100)
        city: str = Field(max_length=50)
        zip_code: str = Field(max_length=10)

    class Person(BoundedModel):
        name: str = Field(max_length=100)
        age: int = Field(ge=0, le=150)
        addresses: list[Address] = Field(max_length=5)

    class Company(BoundedModel):
        name: str = Field(max_length=200)
        employees: list[Person] = Field(max_length=1000)
        revenue: float = Field(ge=0.0, le=1e12)

    assert Address.is_bounded()
    assert Person.is_bounded()
    assert Company.is_bounded()

    # Now create one with unbounded fields
    class UnboundedPerson(BoundedModel):
        name: str  # Missing max_length
        age: int = Field(ge=0)  # Missing upper bound

    class CompanyWithUnbounded(BoundedModel):
        name: str = Field(max_length=200)
        employees: list[UnboundedPerson] = Field(max_length=1000)
        revenue: float = Field(ge=0.0, le=1e12)

    assert not UnboundedPerson.is_bounded()
    assert not CompanyWithUnbounded.is_bounded()
