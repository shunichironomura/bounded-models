"""Tests for field error annotations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, Literal

import pytest
from pydantic import Field

from bounded_models import MissingDefaultError, UnboundedFieldError

if TYPE_CHECKING:
    from typing_extensions import TypeForm


@pytest.mark.parametrize("error_type", [UnboundedFieldError, MissingDefaultError])
@pytest.mark.parametrize(
    "annotation",
    [None, int, list[int], int | str, Literal["a", "b"], Annotated[int, Field(ge=0)]],
)
def test_error_annotation(
    error_type: type[UnboundedFieldError | MissingDefaultError],
    annotation: TypeForm[Any] | None,
) -> None:
    error = error_type("value", annotation)

    assert error.field_name == "value"
    assert error.annotation is annotation
    assert "Field 'value' is unbounded" in str(error)
    if annotation is None:
        assert "(type:" not in str(error)
    else:
        assert f"(type: {annotation})" in str(error)


@pytest.mark.parametrize("error_type", [UnboundedFieldError, MissingDefaultError])
def test_error_without_annotation(error_type: type[UnboundedFieldError | MissingDefaultError]) -> None:
    error = error_type("value")

    assert error.annotation is None
    assert "(type:" not in str(error)
