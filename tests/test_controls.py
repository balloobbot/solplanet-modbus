"""Tests for the write-only inverter control map (UM0058 section 2.5).

The control registers are holding registers, so a write lands in the mock's
holding store — the input store the data maps read stays untouched.
"""

from __future__ import annotations

import pytest
from modbus_connection.mock import MockModbusUnit, WriteEvent

from solplanet_modbus import InverterControls, SolplanetValueValidationError


@pytest.fixture
def controls(mock_modbus_unit: MockModbusUnit) -> InverterControls:
    return InverterControls(mock_modbus_unit)


async def test_adjust_active_power(
    controls: InverterControls, mock_modbus_unit: MockModbusUnit
) -> None:
    """UM0058's worked example: 100 kW inverter, 30 kW now, 50 kW wanted."""
    await controls.async_adjust_active_power(20)
    assert mock_modbus_unit.holding[60000] == 2000


async def test_adjust_active_power_down(
    controls: InverterControls, mock_modbus_unit: MockModbusUnit
) -> None:
    """A negative adjustment is written as a signed 16-bit word."""
    await controls.async_adjust_active_power(-20)
    assert mock_modbus_unit.holding[60000] == 0x10000 - 2000


async def test_curtail_to_zero(
    controls: InverterControls, mock_modbus_unit: MockModbusUnit
) -> None:
    await controls.async_adjust_active_power(-100)
    assert mock_modbus_unit.holding[60000] == 0x10000 - 10000


async def test_active_power_limit(
    controls: InverterControls, mock_modbus_unit: MockModbusUnit
) -> None:
    await controls.async_set_active_power_limit(80)
    assert mock_modbus_unit.holding[60003] == 8000


async def test_power_factor_leading_and_lagging(
    controls: InverterControls, mock_modbus_unit: MockModbusUnit
) -> None:
    await controls.async_set_power_factor(0.95)
    assert mock_modbus_unit.holding[60001] == 9500
    await controls.async_set_power_factor(-0.95)
    assert mock_modbus_unit.holding[60001] == 0x10000 - 9500


async def test_reactive_power(
    controls: InverterControls, mock_modbus_unit: MockModbusUnit
) -> None:
    await controls.async_set_reactive_power(-30)
    assert mock_modbus_unit.holding[60004] == 0x10000 - 3000


async def test_turn_on_and_off(
    controls: InverterControls, mock_modbus_unit: MockModbusUnit
) -> None:
    await controls.async_turn_on()
    assert mock_modbus_unit.holding[60002] == 1
    await controls.async_turn_off()
    assert mock_modbus_unit.holding[60002] == 2


async def test_controls_write_as_function_code_06(
    controls: InverterControls, mock_modbus_unit: MockModbusUnit
) -> None:
    """UM0058 documents only FC06 for these, so writes stay single-register."""
    events: list[WriteEvent] = []
    mock_modbus_unit.on_write(events.append)

    await controls.async_set_active_power_limit(50)

    assert events == [WriteEvent("holding", 60003, [5000], 0x06)]
    assert mock_modbus_unit.holding == {60003: 5000}


@pytest.mark.parametrize("percent", [101, -101])
async def test_active_power_adjustment_is_bounded(
    controls: InverterControls, percent: float
) -> None:
    with pytest.raises(SolplanetValueValidationError, match="outside the allowed"):
        await controls.async_adjust_active_power(percent)


async def test_active_power_limit_is_bounded(controls: InverterControls) -> None:
    with pytest.raises(SolplanetValueValidationError):
        await controls.async_set_active_power_limit(111)


async def test_reactive_power_is_bounded(controls: InverterControls) -> None:
    with pytest.raises(SolplanetValueValidationError):
        await controls.async_set_reactive_power(66)


@pytest.mark.parametrize("power_factor", [0.5, -0.5, 0])
async def test_power_factor_rejects_the_unusable_band(
    controls: InverterControls, power_factor: float
) -> None:
    """Only 0.75..1 leading and -1..-0.75 lagging mean anything."""
    with pytest.raises(SolplanetValueValidationError, match="excluded range"):
        await controls.async_set_power_factor(power_factor)


async def test_power_factor_rejects_values_beyond_unity(
    controls: InverterControls,
) -> None:
    with pytest.raises(SolplanetValueValidationError, match="outside the allowed"):
        await controls.async_set_power_factor(1.5)


async def test_a_failed_validation_writes_nothing(
    controls: InverterControls, mock_modbus_unit: MockModbusUnit
) -> None:
    with pytest.raises(SolplanetValueValidationError):
        await controls.async_set_active_power_limit(200)
    assert mock_modbus_unit.holding == {}
