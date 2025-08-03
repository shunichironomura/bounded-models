from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from ._registry import is_model_bounded


class BoundedModel(BaseModel):
    """Base class for bounded models.

    This class ensures that all fields in the model are properly bounded.
    """

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        """Validate that the model is properly bounded when subclassed."""
        super().__pydantic_init_subclass__(**kwargs)

        # Check if the model is properly bounded
        if not is_model_bounded(cls):
            msg = f"Model {cls.__name__} is not properly bounded. All fields must have appropriate bounds defined."
            raise ValueError(msg)
