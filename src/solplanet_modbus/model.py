"""The component base classes layered on ``modbus_connection.model``.

The field factories (``gauge``, ``integer``, ``string`` ...) come straight from
that framework; this module only adds what it does not already provide: the
register space every data map lives in, and a bounded-write validator for the
control map.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from modbus_connection.model import Component, NumberField

from .const import NAN_S32, NAN_U32
from .exceptions import SolplanetValueValidationError


class SolplanetComponent(Component):
    """An Ai-logger data map.

    All measured data lives in the input register space: UM0058 allows function
    code 04 for it, and reserves the holding registers for the control map.
    """

    register_space = "input"


class SolplanetControlComponent(Component):
    """A write-only Ai-logger control map.

    The control registers are holding registers with write-only access, so this
    is never polled — :meth:`Component.write` is the only entry point, and it
    goes out as function code 06, the only write UM0058 documents for them.
    """

    register_space = "holding"


# modbus-connection's own uint32/int32 factories do not expose ``nan``, so the
# 32-bit fields are built from NumberField here to carry the protocol's sentinel.
def uint32(
    address: int, *, scale: float = 1.0, unit: str | None = None
) -> NumberField[int]:
    """An unsigned 32-bit value whose unimplemented sentinel decodes to None."""
    return NumberField(
        address, count=2, signed=False, scale=scale, nan=NAN_U32, unit=unit
    )


def int32(
    address: int, *, scale: float = 1.0, unit: str | None = None
) -> NumberField[int]:
    """A signed 32-bit value whose unimplemented sentinel decodes to None."""
    return NumberField(
        address, count=2, signed=True, scale=scale, nan=NAN_S32, unit=unit
    )


def bounded(
    min_value: float,
    max_value: float,
    *,
    excluded: tuple[float, float] | None = None,
) -> Callable[[Any], Any]:
    """Return a write validator rejecting values outside ``min_value..max_value``.

    Passed as a field's ``writable`` argument: modbus-connection calls it with
    the requested value before encoding, and a raise aborts the write. Pass
    ``excluded`` for the control registers whose range has a hole in the middle
    — the power factor command, which is only meaningful away from zero.
    """

    def validate(value: Any) -> Any:
        number = float(value)
        if not min_value <= number <= max_value:
            raise SolplanetValueValidationError(
                f"Value {value} is outside the allowed range {min_value}..{max_value}"
            )
        if excluded is not None and excluded[0] < number < excluded[1]:
            raise SolplanetValueValidationError(
                f"Value {value} is inside the excluded range "
                f"{excluded[0]}..{excluded[1]}"
            )
        return value

    return validate
