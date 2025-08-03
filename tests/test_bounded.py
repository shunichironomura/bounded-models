from typing import Annotated, Any, get_origin

import annotated_types
import pytest
from pydantic import BaseModel, Field

from bounded_models import is_model_bounded
from bounded_models._checkers import BoundednessChecker
from bounded_models._registry import BoundednessCheckerRegistry


def test_no_fields() -> None:
    class ModelWithNoFields(BaseModel):
        """A simple bounded model with no fields."""

    assert is_model_bounded(ModelWithNoFields)


@pytest.mark.xfail(reason="This should be fixed in the future")
def test_numeric_bounds() -> None:
    class ProperlyBoundedNumeric(BaseModel):
        bounded_float: Annotated[list[Annotated[float, Field(ge=0.0, le=1.0)]], Field(max_length=10)]
        bounded_int: int = Field(gt=0, lt=100)  # `= Field` notation
        bounded_float_mixed: Annotated[float, Field(ge=0.0, lt=1.0)]  # Annotated type with bounds

    assert is_model_bounded(ProperlyBoundedNumeric)

    class UnboundedNumeric1(BaseModel):
        unbounded_float: float

    assert not is_model_bounded(UnboundedNumeric1)

    class UnboundedNumeric2(BaseModel):
        only_lower_float: float = Field(ge=0.0)

    assert not is_model_bounded(UnboundedNumeric2)

    class UnboundedNumeric3(BaseModel):
        only_upper_int: int = Field(le=100)

    assert not is_model_bounded(UnboundedNumeric3)


@pytest.mark.xfail(reason="This should be fixed in the future")
def test_string_bounds() -> None:
    class ProperlyBoundedString(BaseModel):
        bounded_str: str = Field(max_length=50)
        bounded_str_with_min: str = Field(min_length=1, max_length=100)

    assert is_model_bounded(ProperlyBoundedString)

    class UnboundedString1(BaseModel):
        unbounded_str: str

    assert not is_model_bounded(UnboundedString1)

    class UnboundedString2(BaseModel):
        only_min_length: str = Field(min_length=1)

    assert not is_model_bounded(UnboundedString2)


@pytest.mark.xfail(reason="This should be fixed in the future")
def test_sequence_bounds() -> None:
    class ProperlyBoundedSequence(BaseModel):
        bounded_list: Annotated[list[str], Field(max_length=10)]
        bounded_tuple: tuple[int, ...] = Field(max_length=5)
        bounded_set: set[float] = Field(max_length=20)

    assert is_model_bounded(ProperlyBoundedSequence)

    class UnboundedSequence1(BaseModel):
        unbounded_list: list[int]

    assert not is_model_bounded(UnboundedSequence1)

    class UnboundedSequence2(BaseModel):
        unbounded_tuple: tuple[str, ...]

    assert not is_model_bounded(UnboundedSequence2)

    class UnboundedSequence3(BaseModel):
        unbounded_set: set[float]

    assert not is_model_bounded(UnboundedSequence3)


@pytest.mark.xfail(reason="We should address this in the future")
def test_optional_fields() -> None:
    class BoundedModelWithOptionals(BaseModel):
        optional_bounded_float: float | None = Field(ge=0.0, le=1.0)

    assert is_model_bounded(BoundedModelWithOptionals)

    class UnboundedModelWithOptionals1(BaseModel):
        optional_bounded_str: str | None = Field(max_length=50)

    assert not is_model_bounded(UnboundedModelWithOptionals1)

    class UnboundedModelWithOptionals2(BaseModel):
        optional_unbounded_int: int | None = None

    assert not is_model_bounded(UnboundedModelWithOptionals2)


def test_nested_bounded_models() -> None:
    class InnerBounded(BaseModel):
        value: float = Field(ge=0.0, le=1.0)

    class InnerUnbounded(BaseModel):
        value: float

    class OuterWithBoundedInner(BaseModel):
        inner: InnerBounded
        count: int = Field(ge=0, le=100)

    class OuterWithUnboundedInner(BaseModel):
        inner: InnerUnbounded
        count: int = Field(ge=0, le=100)

    assert is_model_bounded(InnerBounded)
    assert not is_model_bounded(InnerUnbounded)
    assert is_model_bounded(OuterWithBoundedInner)
    assert not is_model_bounded(OuterWithUnboundedInner)


def test_mixed_bounded_unbounded() -> None:
    class MixedModel(BaseModel):
        bounded_float: float = Field(ge=0.0, le=1.0)
        unbounded_float: float
        bounded_str: str = Field(max_length=50)
        unbounded_list: list[int]
        bounded_list: list[str] = Field(max_length=10)

    assert not is_model_bounded(MixedModel)


def test_custom_type_checker() -> None:
    # Test registering a custom checker for dict types

    registry = BoundednessCheckerRegistry.default()

    class DictChecker(BoundednessChecker):
        def can_handle(self, field_info: Any) -> bool:
            return get_origin(field_info.annotation) is dict or field_info.annotation is dict

        def check(self, field_info: Any, registry: BoundednessCheckerRegistry) -> bool:  # noqa: ARG002
            # Check for max_length constraint
            return any(isinstance(m, annotated_types.MaxLen) for m in field_info.metadata)

    registry.register(DictChecker())

    class ModelWithDict(BaseModel):
        bounded_dict: dict[str, int] = Field(max_length=10)
        unbounded_dict: dict[str, str]

    assert not registry.check_model(ModelWithDict)


@pytest.mark.xfail(reason="This should be fixed in the future")
def test_complex_nested_structure() -> None:
    class Address(BaseModel):
        street: str = Field(max_length=100)
        city: str = Field(max_length=50)
        zip_code: str = Field(max_length=10)

    class Person(BaseModel):
        name: str = Field(max_length=100)
        age: int = Field(ge=0, le=150)
        addresses: list[Address] = Field(max_length=5)

    class Company(BaseModel):
        name: str = Field(max_length=200)
        employees: list[Person] = Field(max_length=1000)
        revenue: float = Field(ge=0.0, le=1e12)

    assert is_model_bounded(Address)
    assert is_model_bounded(Person)
    assert is_model_bounded(Company)

    # Now create one with unbounded fields
    class UnboundedPerson(BaseModel):
        name: str  # Missing max_length
        age: int = Field(ge=0)  # Missing upper bound

    class CompanyWithUnbounded(BaseModel):
        name: str = Field(max_length=200)
        employees: list[UnboundedPerson] = Field(max_length=1000)
        revenue: float = Field(ge=0.0, le=1e12)

    assert not is_model_bounded(UnboundedPerson)
    assert not is_model_bounded(CompanyWithUnbounded)
