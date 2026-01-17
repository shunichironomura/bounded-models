from enum import Enum, Flag, IntEnum, IntFlag, StrEnum

import pytest
from pydantic.fields import FieldInfo

from bounded_models import EnumFieldHandler, FieldHandlerRegistry


class Color(Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


class Status(Enum):
    PENDING = 1
    ACTIVE = 2
    COMPLETED = 3


class SingleValue(Enum):
    ONLY = "only"


class Priority(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


class HttpMethod(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"


class Permission(Flag):
    READ = 1
    WRITE = 2
    EXECUTE = 4


class FileMode(IntFlag):
    READ = 4
    WRITE = 2
    EXECUTE = 1


@pytest.fixture
def handler() -> EnumFieldHandler:
    """Create an enum handler instance."""
    return EnumFieldHandler()


@pytest.fixture
def registry(handler: EnumFieldHandler) -> FieldHandlerRegistry:
    """Create a type handler registry instance."""
    return FieldHandlerRegistry(handlers=[handler])


_BOUNDED_FIELDS = [
    FieldInfo(annotation=Color),
    FieldInfo(annotation=Status),
    FieldInfo(annotation=SingleValue),
    FieldInfo(annotation=Priority),
    FieldInfo(annotation=HttpMethod),
    FieldInfo(annotation=Permission),
    FieldInfo(annotation=FileMode),
]

_UNBOUNDED_FIELDS: list[FieldInfo] = []

_INVALID_FIELDS = [
    FieldInfo(annotation=str),
    FieldInfo(annotation=int),
    FieldInfo(annotation=list),
]


@pytest.mark.parametrize(
    ("field_info", "can_handle", "bounded"),
    [(field_info, True, True) for field_info in _BOUNDED_FIELDS]
    + [(field_info, True, False) for field_info in _UNBOUNDED_FIELDS]
    + [(field_info, False, None) for field_info in _INVALID_FIELDS],
)
def test_enum_handler(
    handler: EnumFieldHandler,
    registry: FieldHandlerRegistry,
    *,
    field_info: FieldInfo,
    can_handle: bool,
    bounded: bool | None,
) -> None:
    """Test enum handler for boundedness."""
    assert handler.can_handle(field_info) == can_handle
    if can_handle:
        assert handler.check_boundedness(field_info, registry) == bounded
        assert handler.n_dimensions(field_info, registry) == 1


@pytest.mark.parametrize(
    ("field_info", "unit_value", "expected"),
    [
        # Color enum: RED=0, GREEN=1, BLUE=2
        (FieldInfo(annotation=Color), 0.0, Color.RED),
        (FieldInfo(annotation=Color), 0.33, Color.RED),
        (FieldInfo(annotation=Color), 0.34, Color.GREEN),
        (FieldInfo(annotation=Color), 0.66, Color.GREEN),
        (FieldInfo(annotation=Color), 0.67, Color.BLUE),
        (FieldInfo(annotation=Color), 1.0, Color.BLUE),
        # Status enum: PENDING=0, ACTIVE=1, COMPLETED=2
        (FieldInfo(annotation=Status), 0.0, Status.PENDING),
        (FieldInfo(annotation=Status), 0.5, Status.ACTIVE),
        (FieldInfo(annotation=Status), 0.99, Status.COMPLETED),
        # SingleValue enum
        (FieldInfo(annotation=SingleValue), 0.0, SingleValue.ONLY),
        (FieldInfo(annotation=SingleValue), 0.5, SingleValue.ONLY),
        (FieldInfo(annotation=SingleValue), 1.0, SingleValue.ONLY),
        # IntEnum
        (FieldInfo(annotation=Priority), 0.0, Priority.LOW),
        (FieldInfo(annotation=Priority), 0.5, Priority.MEDIUM),
        (FieldInfo(annotation=Priority), 1.0, Priority.HIGH),
        # StrEnum
        (FieldInfo(annotation=HttpMethod), 0.0, HttpMethod.GET),
        (FieldInfo(annotation=HttpMethod), 0.5, HttpMethod.POST),
        (FieldInfo(annotation=HttpMethod), 1.0, HttpMethod.PUT),
        # Flag
        (FieldInfo(annotation=Permission), 0.0, Permission.READ),
        (FieldInfo(annotation=Permission), 0.5, Permission.WRITE),
        (FieldInfo(annotation=Permission), 1.0, Permission.EXECUTE),
        # IntFlag
        (FieldInfo(annotation=FileMode), 0.0, FileMode.READ),
        (FieldInfo(annotation=FileMode), 0.5, FileMode.WRITE),
        (FieldInfo(annotation=FileMode), 1.0, FileMode.EXECUTE),
    ],
)
def test_enum_handler_sample(
    handler: EnumFieldHandler,
    registry: FieldHandlerRegistry,
    *,
    field_info: FieldInfo,
    unit_value: float,
    expected: Enum,
) -> None:
    """Test enum handler sampling."""
    result = handler.sample([unit_value], field_info, registry)
    assert result == expected
