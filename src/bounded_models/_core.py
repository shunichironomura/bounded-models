from __future__ import annotations

from pydantic import BaseModel

from ._registry import is_model_bounded


class BoundedModel(BaseModel):
    """Base class for bounded models.

    This class can be used to define models with bounded fields.
    It inherits from `pydantic.BaseModel` and can be extended with additional functionality.
    """

    @classmethod
    def is_bounded(cls) -> bool:
        """Check if all fields in the model are properly bounded.

        Returns:
            True if the model is properly bounded according to the rules, False otherwise.

        Rules for bounded fields:
        - float/int: Must have both lower (ge/gt) and upper (le/lt) bounds
        - str: Must have max_length (and optionally min_length)
        - list/tuple/set: Must have max_length/max_items (and optionally min_length/min_items)
        - BoundedModel: Recursively check nested models

        """
        return is_model_bounded(cls)
