"""Tests for constant field behavior (allow_constants parameter)."""

from typing import Literal

import pytest
from pydantic import BaseModel, Field

from bounded_models import (
    BoundedModel,
    FieldHandlerRegistry,
    MissingDefaultError,
    NumericFieldHandler,
    StringFieldHandler,
    UnboundedFieldError,
    field_dimensions,
    model_dimensions,
)


class ConfigWithConstants(BaseModel):
    """Model with a mix of bounded and constant fields."""

    # Use int with default (unbounded numeric)
    count: int = 42
    rate: float = Field(ge=0.0, le=1.0)  # Bounded


class ConfigWithLiteral(BaseModel):
    """Model with Literal constants."""

    mode: Literal["fast", "slow"] = "fast"  # Literal is always bounded
    rate: float = Field(ge=0.0, le=1.0)  # Bounded


class ConfigWithoutDefault(BaseModel):
    """Model with unbounded field without default."""

    count: int  # Unbounded without default
    rate: float = Field(ge=0.0, le=1.0)


class FullyBoundedConfig(BaseModel):
    """Model where all fields are bounded."""

    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)


@pytest.fixture
def registry() -> FieldHandlerRegistry:
    """Create a default registry instance."""
    return FieldHandlerRegistry.default()


class TestFieldDimensions:
    """Tests for field_dimensions with allow_constants."""

    def test_bounded_field_dimensions(self, registry: FieldHandlerRegistry) -> None:
        """Bounded fields return their actual dimensions."""
        info = ConfigWithConstants.model_fields["rate"]
        assert registry.field_dimensions(info, allow_constants=True) == 1
        assert registry.field_dimensions(info, allow_constants=False) == 1

    def test_constant_field_dimensions_allow(self, registry: FieldHandlerRegistry) -> None:
        """Constant fields return 0 dimensions when allow_constants=True."""
        info = ConfigWithConstants.model_fields["count"]
        assert registry.field_dimensions(info, allow_constants=True) == 0

    def test_constant_field_dimensions_disallow(self, registry: FieldHandlerRegistry) -> None:
        """Constant fields raise UnboundedFieldError when allow_constants=False."""
        info = ConfigWithConstants.model_fields["count"]
        with pytest.raises(UnboundedFieldError):
            registry.field_dimensions(info, allow_constants=False, field_name="count")

    def test_unbounded_no_default_raises(self, registry: FieldHandlerRegistry) -> None:
        """Unbounded field without default raises MissingDefaultError."""
        info = ConfigWithoutDefault.model_fields["count"]
        with pytest.raises(MissingDefaultError):
            registry.field_dimensions(info, allow_constants=True, field_name="count")

    def test_literal_field_always_bounded(self, registry: FieldHandlerRegistry) -> None:
        """Literal fields are always bounded (finite set of values)."""
        info = ConfigWithLiteral.model_fields["mode"]
        # Literal is bounded, so it has 1 dimension regardless of allow_constants
        assert registry.field_dimensions(info, allow_constants=True) == 1
        assert registry.field_dimensions(info, allow_constants=False) == 1


class TestModelDimensions:
    """Tests for model_dimensions with allow_constants."""

    def test_fully_bounded_model(self, registry: FieldHandlerRegistry) -> None:
        """Fully bounded model returns same dimensions either way."""
        assert registry.model_dimensions(FullyBoundedConfig, allow_constants=True) == 2
        assert registry.model_dimensions(FullyBoundedConfig, allow_constants=False) == 2

    def test_model_with_constants(self, registry: FieldHandlerRegistry) -> None:
        """Model with constants returns only bounded field dimensions."""
        # 'count' is unbounded (constant=0 dims), 'rate' is bounded (1 dim)
        assert registry.model_dimensions(ConfigWithConstants, allow_constants=True) == 1

    def test_model_with_constants_disallow(self, registry: FieldHandlerRegistry) -> None:
        """Model with constants raises when allow_constants=False."""
        with pytest.raises(UnboundedFieldError):
            registry.model_dimensions(ConfigWithConstants, allow_constants=False)

    def test_model_without_default_raises(self, registry: FieldHandlerRegistry) -> None:
        """Model with unbounded field without default raises MissingDefaultError."""
        with pytest.raises(MissingDefaultError):
            registry.model_dimensions(ConfigWithoutDefault, allow_constants=True)

    def test_model_with_literal(self, registry: FieldHandlerRegistry) -> None:
        """Model with Literal field (Literal is bounded)."""
        # Literal "mode" is bounded (1 dim), float "rate" is bounded (1 dim)
        assert registry.model_dimensions(ConfigWithLiteral, allow_constants=True) == 2
        assert registry.model_dimensions(ConfigWithLiteral, allow_constants=False) == 2


class TestSampleModel:
    """Tests for sample_model with allow_constants."""

    def test_sample_model_with_constants(self, registry: FieldHandlerRegistry) -> None:
        """Model with constants uses default values."""
        result = registry.sample_model([0.5], ConfigWithConstants)
        assert result.count == 42  # Default value
        assert result.rate == 0.5  # Sampled

    def test_sample_fully_bounded(self, registry: FieldHandlerRegistry) -> None:
        """Fully bounded model samples all fields."""
        result = registry.sample_model([0.25, 0.75], FullyBoundedConfig)
        assert result.x == 0.25
        assert result.y == 0.75

    def test_sample_model_disallow_constants(self, registry: FieldHandlerRegistry) -> None:
        """sample_model with allow_constants=False raises for constants."""
        with pytest.raises(UnboundedFieldError):
            registry.sample_model([0.5], ConfigWithConstants, allow_constants=False)

    def test_sample_model_without_default(self, registry: FieldHandlerRegistry) -> None:
        """sample_model raises MissingDefaultError for unbounded without default."""
        with pytest.raises(MissingDefaultError):
            registry.sample_model([0.5], ConfigWithoutDefault)


class TestModuleLevelFunctions:
    """Tests for module-level convenience functions."""

    def test_field_dimensions_default(self) -> None:
        """field_dimensions defaults to allow_constants=True."""
        info = ConfigWithConstants.model_fields["count"]
        assert field_dimensions(info) == 0  # Constant

    def test_field_dimensions_disallow(self) -> None:
        """field_dimensions with allow_constants=False raises."""
        info = ConfigWithConstants.model_fields["count"]
        with pytest.raises(UnboundedFieldError):
            field_dimensions(info, allow_constants=False)

    def test_model_dimensions_default(self) -> None:
        """model_dimensions defaults to allow_constants=True."""
        assert model_dimensions(ConfigWithConstants) == 1  # Only rate

    def test_model_dimensions_disallow(self) -> None:
        """model_dimensions with allow_constants=False raises."""
        with pytest.raises(UnboundedFieldError):
            model_dimensions(ConfigWithConstants, allow_constants=False)


class TestBoundedModelAllowConstants:
    """Tests for BoundedModel with __allow_constants__."""

    def test_bounded_model_strict_default(self) -> None:
        """BoundedModel defaults to strict (no constants allowed)."""
        with pytest.raises(ValueError, match="not properly bounded"):

            class BadModel(BoundedModel):
                count: int = 42  # Unbounded - should fail

    def test_bounded_model_strict_success(self) -> None:
        """BoundedModel with all bounded fields succeeds."""

        class GoodModel(BoundedModel):
            x: float = Field(ge=0, le=1)
            y: float = Field(ge=0, le=1)

        assert GoodModel(x=0.5, y=0.5)

    def test_bounded_model_allow_constants(self) -> None:
        """BoundedModel with __allow_constants__=True allows constants."""

        class LenientModel(BoundedModel):
            __allow_constants__ = True
            count: int = 42  # OK: has default
            x: float = Field(ge=0, le=1)

        instance = LenientModel(count=10, x=0.5)
        assert instance.count == 10
        assert instance.x == 0.5

    def test_bounded_model_allow_constants_no_default_fails(self) -> None:
        """BoundedModel with __allow_constants__=True still requires defaults."""
        with pytest.raises(MissingDefaultError):

            class BadLenientModel(BoundedModel):
                __allow_constants__ = True
                count: int  # Unbounded without default - should fail
                x: float = Field(ge=0, le=1)

    def test_bounded_model_inheritance(self) -> None:
        """__allow_constants__ is inherited by subclasses."""

        class BaseLenient(BoundedModel):
            __allow_constants__ = True

        class DerivedLenient(BaseLenient):
            count: int = 42  # OK because parent allows constants
            x: float = Field(ge=0, le=1)

        instance = DerivedLenient(count=10, x=0.5)
        assert instance.count == 10


class TestExceptionMessages:
    """Tests for exception message quality."""

    def test_unbounded_field_error_message(self, registry: FieldHandlerRegistry) -> None:
        """UnboundedFieldError includes field name and type."""
        info = ConfigWithConstants.model_fields["count"]
        with pytest.raises(UnboundedFieldError) as exc_info:
            registry.field_dimensions(info, allow_constants=False, field_name="count")
        assert "count" in str(exc_info.value)
        assert "int" in str(exc_info.value)

    def test_missing_default_error_message(self, registry: FieldHandlerRegistry) -> None:
        """MissingDefaultError includes field name and type."""
        info = ConfigWithoutDefault.model_fields["count"]
        with pytest.raises(MissingDefaultError) as exc_info:
            registry.field_dimensions(info, allow_constants=True, field_name="count")
        assert "count" in str(exc_info.value)
        assert "int" in str(exc_info.value)


class TestDefaultFactory:
    """Tests for default_factory support."""

    def test_default_factory_with_custom_registry(self) -> None:
        """default_factory works for constant fields (using custom registry with StringHandler)."""
        # Create a custom registry that includes StringFieldHandler
        registry = FieldHandlerRegistry(
            handlers=[
                NumericFieldHandler(),
                StringFieldHandler(),
            ],
        )

        class ConfigWithFactory(BaseModel):
            tags: str = Field(default_factory=lambda: "default_tag")
            rate: float = Field(ge=0.0, le=10.0)

        # tags is unbounded string with default_factory, rate is bounded
        assert registry.model_dimensions(ConfigWithFactory, allow_constants=True) == 1

        # Sample should use the factory (unit value 0.5 maps to rate=5.0)
        result = registry.sample_model([0.5], ConfigWithFactory, allow_constants=True)
        assert result.tags == "default_tag"
        assert result.rate == 5.0
