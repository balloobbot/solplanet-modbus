"""Tests for the reconstructed inverter error code table."""

from __future__ import annotations

import pytest
from modbus_connection.mock import MockModbusUnit

from solplanet_modbus import INVERTER_ERROR_CODES, Inverter, error_description


@pytest.mark.parametrize(
    ("code", "description"),
    [
        (0, "No error"),
        (35, "Utility loss"),
        (37, "PV over voltage"),
        (305, "Inverter offline"),
        (2002, "Battery disconnected"),
        (2047, "Voltage DC component over limit"),
    ],
)
def test_known_codes_are_labelled(code: int, description: str) -> None:
    assert error_description(code) == description


@pytest.mark.parametrize("code", [12, 20, 66, 999, 2022, 65534])
def test_unknown_and_reserved_codes_have_no_label(code: int) -> None:
    """Reserved placeholders are omitted, so they read as unknown, not as a label."""
    assert error_description(code) is None


def test_no_code_without_an_error() -> None:
    assert error_description(None) is None


def test_the_table_is_not_accidentally_truncated() -> None:
    assert len(INVERTER_ERROR_CODES) > 80
    assert max(INVERTER_ERROR_CODES) == 2047


async def test_error_description_reads_from_the_register(
    unit: MockModbusUnit,
) -> None:
    unit.input[1377] = 35
    inverter = Inverter.for_modbus_id(unit, 3)
    await inverter.async_update()
    assert inverter.data.error_code == 35
    assert inverter.data.error_description == "Utility loss"


async def test_an_unknown_code_keeps_its_raw_value(unit: MockModbusUnit) -> None:
    """The label is additive: an unmapped code must not lose the number."""
    unit.input[1377] = 4242
    inverter = Inverter.for_modbus_id(unit, 3)
    await inverter.async_update()
    assert inverter.data.error_code == 4242
    assert inverter.data.error_description is None
