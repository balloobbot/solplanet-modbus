"""One inverter's data, as the Ai-logger republishes it (UM0058 section 2.2).

Fields are declared in the coordinates of the first window — COM1, Modbus
address 3, registers 1000-1389 — and every other window is that same layout
shifted by an :class:`~solplanet_modbus.addressing.InverterSlot`'s
``base_offset``. Registers 1124-1299 of a window are reserved, so the layout
splits into a static identity block and a runtime data block.

Two register addresses in UM0058 V03 are typos and are corrected here: PV7
voltage is printed as ``31330`` (it is 1330, matching the two-register PV
stride), and the slave CPU sub-version range as ``1103~1015`` (it is 1103-1105,
mirroring the master CPU sub-version's three registers).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from modbus_connection.model import (
    enum,
    gauge,
    int32,
    integer,
    repeating_group,
    string,
    uint32,
)

from .addressing import InverterSlot, slot_for
from .const import NAN_E16, NAN_S16, NAN_S32, NAN_U16, NAN_U32
from .enums import DeviceState, FaultState, InverterModel, PhaseType
from .errors import error_description
from .model import SolplanetComponent

if TYPE_CHECKING:
    from modbus_connection import ModbusUnit

#: PV inputs and strings a window reserves, whether or not the inverter has them.
PV_INPUT_COUNT = 10
STRING_COUNT = 20


class PvInput(SolplanetComponent):
    """One PV input of an inverter.

    Declares no readable range of its own: its addresses are read as part of the
    :class:`InverterData` block it belongs to.
    """

    voltage = gauge(1318, 0.1, signed=False, nan=NAN_U16, unit="V")
    current = gauge(1319, 0.01, signed=False, nan=NAN_U16, unit="A")


class PvString(SolplanetComponent):
    """One monitored PV string of an inverter. Read with :class:`InverterData`."""

    current = gauge(1338, 0.1, signed=False, nan=NAN_U16, unit="A")


class InverterInfo(SolplanetComponent):
    """An inverter's identity, ratings and firmware versions.

    These registers do not change while the inverter runs, so this is normally
    read once at setup rather than polled.
    """

    register_ranges = ((1000, 1123),)

    # Transmitted as a string: one ASCII digit, right-aligned in the register.
    # Read as a number so the digit can be mapped to PhaseType; see `phase_type`.
    _device_type_raw = integer(1000, signed=False)
    modbus_address = integer(1001, signed=False, nan=NAN_U16)
    serial_number = string(1002, 16)
    machine_type = string(1018, 8)
    # UM0058 defers the codes to a "section 3.5" the released manual does not
    # contain, so the raw value is all this library can offer.
    grid_code = integer(1026, signed=False, nan=NAN_U16)
    rated_power = uint32(1027, nan=NAN_U32, unit="W")
    master_software_version = string(1029, 7)
    slave_software_version = string(1036, 7)
    safety_version = string(1043, 7)
    protocol_version = string(1050, 6)
    manufacturer = string(1056, 8)
    brand = string(1064, 8)
    model = enum(1072, InverterModel, nan=NAN_E16)
    mppt_count = integer(1073, signed=False, nan=NAN_U16)
    string_current_count = integer(1074, signed=False, nan=NAN_U16)
    hardware_version = string(1075, 2)
    master_cpu_sub_version = string(1077, 3)
    slave_cpu_version = string(1096, 7)
    slave_cpu_sub_version = string(1103, 3)

    # Each register counts the strings wired to a block of four PV inputs.
    string_count_pv1_4 = integer(1116, signed=False, nan=NAN_U16)
    string_count_pv5_8 = integer(1117, signed=False, nan=NAN_U16)
    string_count_pv9_12 = integer(1118, signed=False, nan=NAN_U16)
    string_count_pv13_16 = integer(1119, signed=False, nan=NAN_U16)
    string_count_pv17_20 = integer(1120, signed=False, nan=NAN_U16)
    string_count_pv21_24 = integer(1121, signed=False, nan=NAN_U16)
    string_count_pv25_28 = integer(1122, signed=False, nan=NAN_U16)
    string_count_pv29_32 = integer(1123, signed=False, nan=NAN_U16)

    @property
    def phase_type(self) -> PhaseType | None:
        """Whether the inverter is single- or three-phase."""
        raw = self._device_type_raw
        if raw is None:
            return None
        try:
            return PhaseType(int(chr(raw & 0xFF)))
        except ValueError:  # not a digit, or a phase count this library knows
            return None

    @property
    def string_counts(self) -> tuple[int | None, ...]:
        """Strings wired per block of four PV inputs, PV1-4 first."""
        return (
            self.string_count_pv1_4,
            self.string_count_pv5_8,
            self.string_count_pv9_12,
            self.string_count_pv13_16,
            self.string_count_pv17_20,
            self.string_count_pv21_24,
            self.string_count_pv25_28,
            self.string_count_pv29_32,
        )


class InverterData(SolplanetComponent):
    """An inverter's live measurements.

    Values UM0058 marks optional belong to hardware an inverter may not have —
    the extra PV inputs, the per-string currents, the L2/L3 and line voltages of
    a single-phase inverter, the DC/DC converter temperature of a non-hybrid.
    Those read either zero or the protocol's unimplemented sentinel, which
    decodes to None (see the NAN_* constants).
    """

    register_ranges = ((1300, 1388),)

    grid_rated_voltage = gauge(1300, 0.1, signed=False, nan=NAN_U16, unit="V")
    grid_rated_frequency = gauge(1301, 0.01, signed=False, nan=NAN_U16, unit="Hz")
    energy_today = uint32(1302, scale=0.1, nan=NAN_U32, unit="kWh")
    energy_total = uint32(1304, scale=0.1, nan=NAN_U32, unit="kWh")
    hours_total = uint32(1306, nan=NAN_U32, unit="h")
    state = enum(1308, DeviceState, nan=NAN_E16)
    connect_time = integer(1309, signed=False, nan=NAN_U16, unit="s")

    internal_temperature = gauge(1310, 0.1, nan=NAN_S16, unit="°C")
    phase_u_temperature = gauge(1311, 0.1, nan=NAN_S16, unit="°C")
    phase_v_temperature = gauge(1312, 0.1, nan=NAN_S16, unit="°C")
    phase_w_temperature = gauge(1313, 0.1, nan=NAN_S16, unit="°C")
    boost_temperature = gauge(1314, 0.1, nan=NAN_S16, unit="°C")
    dc_converter_temperature = gauge(1315, 0.1, nan=NAN_S16, unit="°C")
    bus_voltage = gauge(1316, 0.1, signed=False, nan=NAN_U16, unit="V")

    pv_inputs = repeating_group(PV_INPUT_COUNT, PvInput, stride=2)
    strings = repeating_group(STRING_COUNT, PvString, stride=1)

    l1_voltage = gauge(1358, 0.1, signed=False, nan=NAN_U16, unit="V")
    l1_current = gauge(1359, 0.1, signed=False, nan=NAN_U16, unit="A")
    l2_voltage = gauge(1360, 0.1, signed=False, nan=NAN_U16, unit="V")
    l2_current = gauge(1361, 0.1, signed=False, nan=NAN_U16, unit="A")
    l3_voltage = gauge(1362, 0.1, signed=False, nan=NAN_U16, unit="V")
    l3_current = gauge(1363, 0.1, signed=False, nan=NAN_U16, unit="A")
    rs_line_voltage = gauge(1364, 0.1, signed=False, nan=NAN_U16, unit="V")
    rt_line_voltage = gauge(1365, 0.1, signed=False, nan=NAN_U16, unit="V")
    st_line_voltage = gauge(1366, 0.1, signed=False, nan=NAN_U16, unit="V")
    grid_frequency = gauge(1367, 0.01, signed=False, nan=NAN_U16, unit="Hz")

    apparent_power = uint32(1368, nan=NAN_U32, unit="VA")
    active_power = int32(1370, nan=NAN_S32, unit="W")
    reactive_power = int32(1372, nan=NAN_S32, unit="var")
    power_factor = gauge(1374, 0.01, nan=NAN_S16)

    fault_state = enum(1376, FaultState, nan=NAN_E16)
    # UM0058 defers both code tables to a "section 3.4" the released manual does
    # not contain. `error_description` labels the error code from a table
    # reconstructed elsewhere; no such table exists for the warning code.
    error_code = integer(1377, signed=False, nan=NAN_E16)
    warning_code = integer(1378, signed=False, nan=NAN_E16)
    ios_measure = integer(1388, signed=False, nan=NAN_U16)

    @property
    def error_description(self) -> str | None:
        """Label for :attr:`error_code`, or None if the code has no known meaning.

        The code table is reconstructed rather than documented — see
        :mod:`solplanet_modbus.errors`. Always keep the raw code alongside it.
        """
        return error_description(self.error_code)

    @property
    def pv_voltages(self) -> tuple[float | None, ...]:
        """PV input voltages, PV1 first."""
        return tuple(pv.voltage for pv in self.pv_inputs)

    @property
    def pv_currents(self) -> tuple[float | None, ...]:
        """PV input currents, PV1 first."""
        return tuple(pv.current for pv in self.pv_inputs)

    @property
    def string_currents(self) -> tuple[float | None, ...]:
        """Per-string currents, string 1 first."""
        return tuple(pv_string.current for pv_string in self.strings)


class Inverter:
    """One inverter behind the Ai-logger: its identity and its measurements."""

    def __init__(
        self,
        unit: ModbusUnit,
        *,
        base_offset: int = 0,
        slot: InverterSlot | None = None,
    ) -> None:
        """Build an inverter reading the window at ``base_offset``.

        The default reads registers 1000-1389 unshifted, which is "method 2"
        addressing: the unit is bound to the inverter's own RS485 address, and
        the logger answers with that inverter's data. Use :meth:`for_slot` for
        "method 1", where one unit carries every inverter at its own offset.

        ``slot`` records which window this reads, for a caller holding several.
        """
        #: The window this inverter reads, or None when it was addressed by
        #: unit ID rather than by offset.
        self.slot = slot
        self.info = InverterInfo(unit, base_offset=base_offset)
        self.data = InverterData(unit, base_offset=base_offset)

    @classmethod
    def for_slot(cls, unit: ModbusUnit, slot: InverterSlot) -> Inverter:
        """Build the inverter occupying ``slot`` of the logger's map."""
        return cls(unit, base_offset=slot.base_offset, slot=slot)

    @classmethod
    def for_modbus_id(cls, unit: ModbusUnit, modbus_id: int) -> Inverter:
        """Build the inverter the logger scanned at RS485 address ``modbus_id``.

        Raises :class:`~solplanet_modbus.exceptions.UnknownInverterAddressError`
        for an address outside the documented port ranges.
        """
        return cls.for_slot(unit, slot_for(modbus_id))

    async def async_update(self) -> None:
        """Refresh the measurements, leaving the identity block untouched."""
        await self.data.async_update()

    async def async_update_info(self) -> None:
        """Refresh the identity block."""
        await self.info.async_update()
