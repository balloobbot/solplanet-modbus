"""End-to-end tests of the object model over the in-memory mock backend."""

from __future__ import annotations

import pytest
from modbus_connection import (
    IllegalDataAddressError,
    ModbusConnectionError,
    ServerDeviceFailureError,
)
from modbus_connection.mock import MockModbusUnit

from solplanet_modbus import (
    AiLogger,
    ComPort,
    DeviceState,
    FaultState,
    Inverter,
    InverterModel,
    PhaseType,
    slot_for,
    slots_for_port,
)

from .conftest import INPUT, words_for_string


async def test_inverter_identity(logger: AiLogger) -> None:
    await logger.async_read_info()
    info = logger.inverters[0].info
    assert info.modbus_address == 3
    assert info.serial_number == "QA10010022920081"
    assert info.machine_type == "ASW8000"
    assert info.phase_type is PhaseType.THREE_PHASE
    assert info.rated_power == 20000
    assert info.model is InverterModel.PV_THREE_PHASE_3_10KW
    assert info.mppt_count == 2
    assert info.string_current_count == 4
    assert info.grid_code == 14
    assert info.manufacturer == "AISWEI"
    assert info.brand == "AISWEI"
    assert info.safety_version == "VDE4105"
    assert info.protocol_version == "2.1.5"
    assert info.master_software_version == "V1.0.5"
    assert info.slave_software_version == "V1.0.3"
    assert info.hardware_version == "H2"
    assert info.master_cpu_sub_version == "A01"
    assert info.slave_cpu_version == "V1.0.3"
    assert info.slave_cpu_sub_version == "B02"
    assert info.string_counts == (2, 2, 0, 0, 0, 0, 0, 0)


async def test_identity_is_empty_before_a_read(logger: AiLogger) -> None:
    info = logger.inverters[0].info
    assert info.serial_number is None
    assert info.phase_type is None
    assert info.string_counts == (None,) * 8


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (0x0031, PhaseType.SINGLE_PHASE),
        (0x0033, PhaseType.THREE_PHASE),
        (0x0032, None),  # a digit, but not a phase count the protocol defines
        (0x0041, None),  # not a digit at all
        (0x0000, None),  # an unpopulated window
    ],
)
async def test_phase_type_decodes_the_ascii_digit(
    unit: MockModbusUnit, raw: int, expected: PhaseType | None
) -> None:
    unit.input[1000] = raw
    inverter = Inverter.for_modbus_id(unit, 3)
    await inverter.async_update_info()
    assert inverter.info.phase_type is expected


async def test_inverter_measurements(logger: AiLogger) -> None:
    await logger.async_update()
    data = logger.inverters[0].data
    assert data.state is DeviceState.NORMAL
    assert data.fault_state is FaultState.NO_INTERNAL_FAULT
    assert data.grid_rated_voltage == pytest.approx(230.0)
    assert data.grid_rated_frequency == pytest.approx(50.0)
    assert data.grid_frequency == pytest.approx(50.01)
    assert data.energy_today == pytest.approx(123.4)
    assert data.energy_total == pytest.approx(7000.0)  # crosses the 16-bit boundary
    assert data.hours_total == 8760
    assert data.connect_time == 342
    assert data.internal_temperature == pytest.approx(41.5)
    assert data.boost_temperature == pytest.approx(40.2)
    assert data.bus_voltage == pytest.approx(650.0)
    assert data.apparent_power == 5400
    assert data.active_power == 5389
    assert data.reactive_power == -120  # signed 32-bit
    assert data.power_factor == pytest.approx(0.99)
    assert data.error_code == 0
    assert data.warning_code == 0
    assert data.ios_measure == 7


async def test_inverter_phases_and_line_voltages(logger: AiLogger) -> None:
    await logger.async_update()
    data = logger.inverters[0].data
    assert data.l1_voltage == pytest.approx(231.2)
    assert data.l1_current == pytest.approx(7.8)
    assert data.l2_voltage == pytest.approx(229.8)
    assert data.l3_voltage == pytest.approx(230.5)
    assert data.rs_line_voltage == pytest.approx(399.8)
    assert data.rt_line_voltage == pytest.approx(400.1)
    assert data.st_line_voltage == pytest.approx(399.5)


async def test_pv_inputs_and_strings(logger: AiLogger) -> None:
    await logger.async_update()
    data = logger.inverters[0].data
    assert len(data.pv_inputs) == 10
    assert len(data.strings) == 20
    assert data.pv_inputs[0].voltage == pytest.approx(345.0)
    assert data.pv_inputs[0].current == pytest.approx(5.12)
    assert data.pv_inputs[1].voltage == pytest.approx(338.0)
    assert data.pv_voltages[:3] == pytest.approx([345.0, 338.0, 0.0])
    assert data.pv_currents[:3] == pytest.approx([5.12, 4.98, 0.0])
    assert data.strings[0].current == pytest.approx(25.6)
    assert data.string_currents[:3] == pytest.approx([25.6, 26.1, 0.0])


async def test_each_inverter_reads_its_own_window(logger: AiLogger) -> None:
    """The second inverter is on COM2, 11700 registers further into the map."""
    await logger.async_read_info()
    await logger.async_update()
    first, second = logger.inverters
    assert first.slot is not None and first.slot.port is ComPort.COM1
    assert second.slot is not None and second.slot.port is ComPort.COM2
    assert second.info.modbus_address == 51
    assert second.info.serial_number == "QA10010022920082"
    assert second.data.energy_today == pytest.approx(98.7)
    assert first.data.energy_today == pytest.approx(123.4)


async def test_site_totals(logger: AiLogger) -> None:
    await logger.async_update()
    assert logger.system.active_power == 10778
    assert logger.system.reactive_power == -240


async def test_weather_station(logger: AiLogger) -> None:
    await logger.async_update()
    assert logger.weather is not None
    first, second = logger.weather.sensors
    assert first.wind_speed_raw == 42  # unscaled, as UM0058 documents it
    assert first.irradiance == pytest.approx(812.3)
    assert first.cell_temperature == pytest.approx(31.5)
    assert first.external_temperature_1 == pytest.approx(22.4)
    assert first.external_temperature_2 == pytest.approx(-5.5)
    assert first.humidity == 47
    assert first.wind_direction == 178
    assert second.irradiance == pytest.approx(809.0)
    assert second.cell_temperature == pytest.approx(25.0)


async def test_energy_meter(logger: AiLogger) -> None:
    await logger.async_update()
    meter = logger.meter
    assert meter is not None
    assert meter.l1_voltage == pytest.approx(238.7)
    assert meter.l3_current == pytest.approx(5.98)
    assert meter.l1_power == pytest.approx(-1444.5)  # importing
    assert meter.total_power == pytest.approx(-4328.0)
    assert meter.total_power_factor == pytest.approx(0.99)
    assert meter.frequency == pytest.approx(50.01)
    assert meter.import_energy == pytest.approx(1234.5)
    assert meter.export_energy == pytest.approx(8765.4)
    assert meter.apparent_energy == pytest.approx(8900.1)
    assert meter.l1_l2_voltage == pytest.approx(413.4)
    assert meter.average_line_to_line_voltage == pytest.approx(413.43)


async def test_optional_maps_are_off_by_default(unit: MockModbusUnit) -> None:
    logger = AiLogger(unit, [3])
    assert logger.weather is None
    assert logger.meter is None
    assert logger.components == (logger.system, logger.inverters[0].data)


async def test_each_block_is_one_request(unit: MockModbusUnit) -> None:
    """A refresh costs one read per block: the layout leaves no split to make."""
    logger = AiLogger(unit, [3], weather=True, meter=True)
    unit.read_events.clear()
    await logger.async_update()
    assert [(event.address, event.count) for event in unit.read_events] == [
        (986, 14),  # weather station, both sensors
        (1300, 89),  # inverter measurements
        (36100, 4),  # site totals
        (36104, 102),  # SDM630 meter, gaps included
    ]


async def test_reading_info_leaves_measurements_alone(unit: MockModbusUnit) -> None:
    inverter = Inverter.for_modbus_id(unit, 3)
    await inverter.async_update_info()
    assert inverter.info.serial_number == "QA10010022920081"
    assert inverter.data.active_power is None


async def test_method_2_addressing_reads_the_window_unshifted(
    mock_modbus_unit: MockModbusUnit,
) -> None:
    """With the unit bound to an inverter's own RS485 address, nothing shifts."""
    mock_modbus_unit.input.update(
        {1001: 77, 1371: 4200}
        | {1002 + i: w for i, w in words_for_string("QA9", 16).items()}
    )
    inverter = Inverter(mock_modbus_unit)
    assert inverter.slot is None
    await inverter.async_update_info()
    await inverter.async_update()
    assert inverter.info.modbus_address == 77
    assert inverter.info.serial_number == "QA9"
    assert inverter.data.active_power == 4200


async def test_raw_read_returns_the_words_behind_the_values(logger: AiLogger) -> None:
    raw = await logger.async_read_raw()
    assert raw["input"][36101] == 10778
    assert raw["input"][slot_for(51).base_address + 371] == 5389


async def test_discover_finds_populated_windows(unit: MockModbusUnit) -> None:
    """An occupied window reports its own address back; an empty one reads zero."""
    found = await AiLogger.async_discover(unit, slots_for_port(ComPort.COM1))
    assert [inverter.modbus_id for inverter in found] == [3]
    assert found[0].serial_number == "QA10010022920081"
    assert found[0].machine_type == "ASW8000"
    assert found[0].slot.port is ComPort.COM1


async def test_discover_scans_every_window_by_default(unit: MockModbusUnit) -> None:
    unit.read_events.clear()
    found = await AiLogger.async_discover(unit)
    assert [inverter.modbus_id for inverter in found] == [3, 51]
    assert len(unit.read_events) == 90  # one identity read per reserved window


async def test_discover_tolerates_a_window_without_identity_strings(
    mock_modbus_unit: MockModbusUnit,
) -> None:
    """A window answering with its address but no strings still discovers."""
    mock_modbus_unit.input.update({1001: 3})
    found = await AiLogger.async_discover(mock_modbus_unit, [slot_for(3)])
    assert found[0].serial_number == ""
    assert found[0].machine_type == ""


async def test_discover_skips_a_window_the_logger_does_not_serve(
    unit: MockModbusUnit,
) -> None:
    """ "Illegal data address" is the same news as an empty window, not a fault."""
    unit.fail_read(
        slot_for(4).base_address,
        IllegalDataAddressError(message="no such window"),
        register_type="input",
    )
    found = await AiLogger.async_discover(unit, slots_for_port(ComPort.COM1))
    assert [inverter.modbus_id for inverter in found] == [3]


async def test_discover_still_raises_on_a_real_fault(unit: MockModbusUnit) -> None:
    """A device failure is not 'nothing here' — it must not be scanned past."""
    unit.fail_read(
        slot_for(4).base_address,
        ServerDeviceFailureError(message="device failed"),
        register_type="input",
    )
    with pytest.raises(ServerDeviceFailureError):
        await AiLogger.async_discover(unit, slots_for_port(ComPort.COM1))


async def test_discover_reports_nothing_from_a_silent_logger(
    mock_modbus_unit: MockModbusUnit,
) -> None:
    """A logger that answers nothing is a failure, not an empty site."""
    mock_modbus_unit.fail_requests(ModbusConnectionError("device is offline"))
    with pytest.raises(ModbusConnectionError):
        await AiLogger.async_discover(mock_modbus_unit, [slot_for(3)])


async def test_a_logger_without_inverters_reads_only_the_totals(
    unit: MockModbusUnit,
) -> None:
    logger = AiLogger(unit)
    assert logger.inverters == ()
    await logger.async_read_info()  # nothing to read, but must not raise
    await logger.async_update()
    assert logger.system.active_power == 10778


def test_the_fixture_covers_both_documented_addressing_methods() -> None:
    """Guard the fixture itself: window 2 really is offset, not duplicated."""
    assert INPUT[1001] == 3
    assert INPUT[slot_for(51).base_address + 1] == 51
