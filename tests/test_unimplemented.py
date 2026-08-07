"""Tests for the protocol's unimplemented-register sentinels.

UM0058 documents no sentinel, but the AISWEI protocol marks a register an
inverter does not implement with the all-ones pattern for an unsigned type and
the sign bit alone for a signed one. Without that, an absent hardware option
decodes to a plausible-looking 6553.5 V or -3276.8 °C.
"""

from __future__ import annotations

import pytest
from modbus_connection.mock import MockModbusUnit

from solplanet_modbus import (
    NAN_E16,
    NAN_S16,
    NAN_S32,
    NAN_U16,
    NAN_U32,
    AiLogger,
    Inverter,
    slot_for,
)


@pytest.mark.parametrize(
    ("address", "sentinel", "field"),
    [
        (1300, NAN_U16, "grid_rated_voltage"),
        (1309, NAN_U16, "connect_time"),
        (1310, NAN_S16, "internal_temperature"),
        (1315, NAN_S16, "dc_converter_temperature"),
        (1316, NAN_U16, "bus_voltage"),
        (1358, NAN_U16, "l1_voltage"),
        (1363, NAN_U16, "l3_current"),
        (1367, NAN_U16, "grid_frequency"),
        (1374, NAN_S16, "power_factor"),
        (1388, NAN_U16, "ios_measure"),
    ],
)
async def test_16_bit_sentinels_decode_to_none(
    unit: MockModbusUnit, address: int, sentinel: int, field: str
) -> None:
    unit.input[address] = sentinel
    inverter = Inverter.for_modbus_id(unit, 3)
    await inverter.async_update()
    assert getattr(inverter.data, field) is None


@pytest.mark.parametrize(
    ("address", "sentinel", "field"),
    [
        (1302, NAN_U32, "energy_today"),
        (1304, NAN_U32, "energy_total"),
        (1306, NAN_U32, "hours_total"),
        (1368, NAN_U32, "apparent_power"),
        (1370, NAN_S32, "active_power"),
        (1372, NAN_S32, "reactive_power"),
    ],
)
async def test_32_bit_sentinels_decode_to_none(
    unit: MockModbusUnit, address: int, sentinel: int, field: str
) -> None:
    unit.input[address] = sentinel >> 16
    unit.input[address + 1] = sentinel & 0xFFFF
    inverter = Inverter.for_modbus_id(unit, 3)
    await inverter.async_update()
    assert getattr(inverter.data, field) is None


async def test_a_signed_sentinel_does_not_swallow_a_real_negative(
    unit: MockModbusUnit,
) -> None:
    """-1 W is a legitimate reading, and only 0x80000000 marks S32 unimplemented."""
    unit.input[1370] = 0xFFFF
    unit.input[1371] = 0xFFFF
    inverter = Inverter.for_modbus_id(unit, 3)
    await inverter.async_update()
    assert inverter.data.active_power == -1


async def test_identity_sentinels_decode_to_none(unit: MockModbusUnit) -> None:
    unit.input.update({1026: NAN_U16, 1072: NAN_E16, 1073: NAN_U16, 1116: NAN_U16})
    unit.input[1027] = NAN_U32 >> 16
    unit.input[1028] = NAN_U32 & 0xFFFF
    inverter = Inverter.for_modbus_id(unit, 3)
    await inverter.async_update_info()
    info = inverter.info
    assert info.grid_code is None
    assert info.model is None
    assert info.mppt_count is None
    assert info.rated_power is None
    assert info.string_counts[0] is None


async def test_enum_sentinels_decode_to_none(unit: MockModbusUnit) -> None:
    """An unread state is None rather than a warning about an unmapped code."""
    unit.input.update({1308: NAN_E16, 1376: NAN_E16, 1377: NAN_E16, 1378: NAN_E16})
    inverter = Inverter.for_modbus_id(unit, 3)
    await inverter.async_update()
    assert inverter.data.state is None
    assert inverter.data.fault_state is None
    assert inverter.data.error_code is None
    assert inverter.data.warning_code is None
    assert inverter.data.error_description is None


async def test_unpopulated_pv_inputs_and_strings_decode_to_none(
    unit: MockModbusUnit,
) -> None:
    unit.input.update({1322: NAN_U16, 1323: NAN_U16, 1340: NAN_U16})
    inverter = Inverter.for_modbus_id(unit, 3)
    await inverter.async_update()
    assert inverter.data.pv_inputs[2].voltage is None
    assert inverter.data.pv_inputs[2].current is None
    assert inverter.data.strings[2].current is None
    assert inverter.data.pv_inputs[0].voltage == pytest.approx(345.0)


async def test_weather_sentinels_decode_to_none(
    logger: AiLogger, unit: MockModbusUnit
) -> None:
    assert logger.weather is not None
    unit.input.update({986: NAN_U16, 988: NAN_S16, 991: NAN_U16})
    await logger.async_update()
    sensor = logger.weather.sensors[0]
    assert sensor.wind_speed_raw is None
    assert sensor.cell_temperature is None
    assert sensor.humidity is None
    assert sensor.irradiance == pytest.approx(812.3)


async def test_site_totals_sentinels_decode_to_none(
    logger: AiLogger, unit: MockModbusUnit
) -> None:
    unit.input.update({36100: NAN_S32 >> 16, 36101: NAN_S32 & 0xFFFF})
    await logger.async_update()
    assert logger.system.active_power is None
    assert logger.system.reactive_power == -240


async def test_sentinels_apply_at_every_window_offset(unit: MockModbusUnit) -> None:
    """The sentinel travels with the field, so it works in a shifted window."""
    unit.input[slot_for(51).base_address + 310] = NAN_S16
    inverter = Inverter.for_modbus_id(unit, 51)
    await inverter.async_update()
    assert inverter.data.internal_temperature is None
