from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel

from ._registry import MissingDefaultError, is_field_bounded, is_model_bounded


class BoundedModel(BaseModel):
    """Base class for bounded models.

    This class ensures that all fields in the model are properly bounded,
    or have default values if __allow_constants__ is True.

    Class Attributes:
        __allow_constants__: If False (default), all fields must be bounded.
                            If True, unbounded fields with defaults are allowed as constants.
    """

    __allow_constants__: ClassVar[bool] = False

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        """Validate that the model is properly bounded when subclassed."""
        super().__pydantic_init_subclass__(**kwargs)

        allow_constants = getattr(cls, "__allow_constants__", False)

        if allow_constants:
            # Lenient mode: unbounded fields must have defaults
            for field_name, field_info in cls.model_fields.items():
                if not is_field_bounded(field_info) and field_info.is_required():
                    raise MissingDefaultError(field_name, field_info.annotation)
        # Strict mode (default): all fields must be bounded
        elif not is_model_bounded(cls):
            msg = f"Model {cls.__name__} is not properly bounded. All fields must have appropriate bounds defined."
            raise ValueError(msg)
