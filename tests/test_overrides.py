"""Tests for field override functionality."""

import pytest
from pydantic import BaseModel, Field

from bounded_models import (
    FieldHandlerRegistry,
    FieldOverride,
    UnboundedFieldError,
    model_dimensions,
)


class ExternalConfig(BaseModel):
    """External model without bounds - simulates a third-party model."""

    learning_rate: float
    batch_size: int


class PartiallyBoundedConfig(BaseModel):
    """Model with some bounded fields."""

    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)


class InnerModel(BaseModel):
    """Inner model for nested testing."""

    value: float


class OuterModel(BaseModel):
    """Outer model with nested inner model."""

    inner: InnerModel
    rate: float = Field(ge=0.0, le=1.0)


class DeeplyNestedModel(BaseModel):
    """Model with deeply nested structure."""

    outer: OuterModel
    x: float = Field(ge=0.0, le=1.0)


@pytest.fixture
def registry() -> FieldHandlerRegistry:
    """Create a default registry instance."""
    return FieldHandlerRegistry.default()


class TestFieldOverrideValidation:
    """Tests for FieldOverride validation."""

    def test_default_and_default_factory_mutually_exclusive(self) -> None:
        """Cannot specify both default and default_factory."""
        with pytest.raises(ValueError, match="Cannot specify both"):
            FieldOverride(default=42, default_factory=lambda: 42)

    def test_default_only(self) -> None:
        """Can specify default alone."""
        override = FieldOverride(default=42)
        assert override.has_default()
        assert override.get_default() == 42

    def test_default_factory_only(self) -> None:
        """Can specify default_factory alone."""
        override = FieldOverride(default_factory=lambda: [1, 2, 3])
        assert override.has_default()
        assert override.get_default() == [1, 2, 3]

    def test_bounds_only(self) -> None:
        """Can specify bounds without default."""
        override = FieldOverride(ge=0.0, le=1.0)
        assert not override.has_default()


class TestAddBoundsToUnboundedField:
    """Tests for adding bounds to unbounded fields via overrides."""

    def test_add_bounds_to_float(self, registry: FieldHandlerRegistry) -> None:
        """Override can add bounds to make unbounded float bounded."""
        overrides = {
            "learning_rate": FieldOverride(ge=1e-5, le=1e-1),
            "batch_size": FieldOverride(ge=1, le=128),
        }

        dims = registry.model_dimensions(
            ExternalConfig,
            overrides=overrides,
        )
        assert dims == 2  # learning_rate + batch_size

    def test_sample_with_bounds_override(self, registry: FieldHandlerRegistry) -> None:
        """Sample model with bounds added via override."""
        overrides = {
            "learning_rate": FieldOverride(ge=0.0, le=1.0),
            "batch_size": FieldOverride(ge=0, le=100),
        }

        result = registry.sample_model(
            [0.5, 0.5],
            ExternalConfig,
            overrides=overrides,
        )

        assert isinstance(result, ExternalConfig)
        assert result.learning_rate == 0.5
        assert result.batch_size == 50


class TestOverrideWithDefault:
    """Tests for overriding fields to be constants."""

    def test_override_with_default_makes_constant(
        self,
        registry: FieldHandlerRegistry,
    ) -> None:
        """Override with default treats field as constant (0 dimensions)."""
        overrides = {"x": FieldOverride(default=0.5)}

        dims = registry.model_dimensions(
            PartiallyBoundedConfig,
            overrides=overrides,
            allow_constants=True,
        )
        # x is now constant (0), y is bounded (1)
        assert dims == 1

    def test_sample_with_default_override(
        self,
        registry: FieldHandlerRegistry,
    ) -> None:
        """Sample uses override default instead of sampling."""
        overrides = {"x": FieldOverride(default=0.25)}

        result = registry.sample_model(
            [0.75],  # Only y is sampled
            PartiallyBoundedConfig,
            overrides=overrides,
            allow_constants=True,
        )

        assert isinstance(result, PartiallyBoundedConfig)
        assert result.x == 0.25  # From override
        assert result.y == 0.75  # Sampled


class TestOverrideWithDefaultFactory:
    """Tests for overriding fields with default_factory."""

    def test_default_factory_makes_constant(
        self,
        registry: FieldHandlerRegistry,
    ) -> None:
        """Override with default_factory treats field as constant."""
        call_count = 0

        def factory() -> float:
            nonlocal call_count
            call_count += 1
            return float(call_count) / 10.0

        overrides = {"x": FieldOverride(default_factory=factory)}

        # Sample twice to verify factory is called each time
        result1 = registry.sample_model(
            [0.5],  # Only y is sampled
            PartiallyBoundedConfig,
            overrides=overrides,
            allow_constants=True,
        )
        result2 = registry.sample_model(
            [0.5],  # Only y is sampled
            PartiallyBoundedConfig,
            overrides=overrides,
            allow_constants=True,
        )

        assert isinstance(result1, PartiallyBoundedConfig)
        assert isinstance(result2, PartiallyBoundedConfig)
        assert result1.x == 0.1  # From factory call 1
        assert result2.x == 0.2  # From factory call 2


class TestNestedModelOverrides:
    """Tests for overriding fields in nested models."""

    def test_nested_override_dimensions(
        self,
        registry: FieldHandlerRegistry,
    ) -> None:
        """Override nested field affects dimensions."""
        overrides = {"inner.value": FieldOverride(ge=0.0, le=10.0)}

        dims = registry.model_dimensions(OuterModel, overrides=overrides)
        # inner.value (1) + rate (1) = 2
        assert dims == 2

    def test_sample_with_nested_override(
        self,
        registry: FieldHandlerRegistry,
    ) -> None:
        """Sample model with nested field override."""
        overrides = {"inner.value": FieldOverride(ge=0.0, le=10.0)}

        result = registry.sample_model(
            [0.5, 0.5],  # inner.value, rate
            OuterModel,
            overrides=overrides,
        )

        assert isinstance(result, OuterModel)
        assert isinstance(result.inner, InnerModel)
        assert result.inner.value == 5.0  # 0.5 * 10
        assert result.rate == 0.5

    def test_nested_default_override(
        self,
        registry: FieldHandlerRegistry,
    ) -> None:
        """Override nested field with default."""
        overrides = {
            "inner.value": FieldOverride(ge=0.0, le=10.0),
            "inner": FieldOverride(default=InnerModel(value=42.0)),
        }

        # When inner has a default, entire nested model is constant
        dims = registry.model_dimensions(
            OuterModel,
            overrides=overrides,
            allow_constants=True,
        )
        assert dims == 1  # Only rate

        result = registry.sample_model(
            [0.75],
            OuterModel,
            overrides=overrides,
            allow_constants=True,
        )
        assert isinstance(result, OuterModel)
        assert result.inner.value == 42.0  # From default
        assert result.rate == 0.75


class TestDeeplyNestedOverrides:
    """Tests for deeply nested model overrides."""

    def test_deeply_nested_override(self, registry: FieldHandlerRegistry) -> None:
        """Override deeply nested field (a.b.c pattern)."""
        overrides = {"outer.inner.value": FieldOverride(ge=0.0, le=100.0)}

        dims = registry.model_dimensions(DeeplyNestedModel, overrides=overrides)
        # outer.inner.value (1) + outer.rate (1) + x (1) = 3
        assert dims == 3

        result = registry.sample_model(
            [0.5, 0.5, 0.5],
            DeeplyNestedModel,
            overrides=overrides,
        )

        assert isinstance(result, DeeplyNestedModel)
        assert result.outer.inner.value == 50.0
        assert result.outer.rate == 0.5
        assert result.x == 0.5


class TestModuleLevelFunctions:
    """Tests for module-level convenience functions with overrides."""

    def test_model_dimensions_with_overrides(self) -> None:
        """model_dimensions accepts overrides parameter."""
        overrides = {
            "learning_rate": FieldOverride(ge=0.0, le=1.0),
            "batch_size": FieldOverride(ge=1, le=100),
        }

        dims = model_dimensions(
            ExternalConfig,
            overrides=overrides,
        )
        assert dims == 2


class TestErrorCases:
    """Tests for error cases with overrides."""

    def test_unbounded_without_override_raises(
        self,
        registry: FieldHandlerRegistry,
    ) -> None:
        """Unbounded field without override still raises error."""
        # Only override some fields, leave learning_rate unbounded
        overrides = {
            "batch_size": FieldOverride(ge=1, le=128),
        }

        with pytest.raises(UnboundedFieldError):
            registry.model_dimensions(ExternalConfig, overrides=overrides)

    def test_override_with_bounds_makes_field_bounded(
        self,
        registry: FieldHandlerRegistry,
    ) -> None:
        """Override with bounds makes unbounded field bounded."""
        overrides = {
            "learning_rate": FieldOverride(ge=0.0, le=1.0),
            "batch_size": FieldOverride(ge=1, le=128),
        }

        # This should work because all fields are bounded via overrides
        dims = registry.model_dimensions(
            ExternalConfig,
            overrides=overrides,
        )
        assert dims == 2
