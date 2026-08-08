"""The top-level Ai-logger device object."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from modbus_connection import BlockReadError, ExceptionCode
from modbus_connection.model import Component, ComponentGroup

from .addressing import InverterSlot, all_slots, slot_for
from .const import AILOGGER_UNIT_ID
from .controls import InverterControls
from .inverter import Inverter, InverterInfo
from .meter import EnergyMeter, SystemPower
from .weather import WeatherStation

if TYPE_CHECKING:
    from modbus_connection import ModbusUnit


@dataclass(frozen=True, slots=True)
class DiscoveredInverter:
    """An inverter a probe found in the logger's map."""

    slot: InverterSlot
    serial_number: str
    machine_type: str

    @property
    def modbus_id(self) -> int:
        """The RS485 address the logger scanned this inverter at."""
        return self.slot.modbus_id


class AiLogger:
    """A Solplanet Ai-logger, read over Modbus TCP.

    The logger reserves 90 inverter windows but a site fills a handful, so the
    caller says which ones exist — from its own configuration, or from what
    :meth:`async_discover` found:

        logger = AiLogger(unit, modbus_ids=[3, 4, 51])
        await logger.async_read_info()   # identity, once
        await logger.async_update()      # measurements, every poll

    ``weather`` and ``meter`` are off by default: reading hardware a site does
    not have wastes a request per poll at best, and the extra registers are of
    no use without the sensor.
    """

    def __init__(
        self,
        unit: ModbusUnit,
        modbus_ids: Iterable[int] = (),
        *,
        weather: bool = False,
        meter: bool = False,
    ) -> None:
        """Build a logger reading the inverters at ``modbus_ids``.

        Raises
        :class:`~solplanet_modbus.exceptions.UnknownInverterAddressError` for an
        address outside the documented port ranges.
        """
        self._unit = unit
        self.inverters: tuple[Inverter, ...] = tuple(
            Inverter.for_slot(unit, slot_for(modbus_id)) for modbus_id in modbus_ids
        )
        self.system = SystemPower(unit)
        self.weather = WeatherStation(unit) if weather else None
        self.meter = EnergyMeter(unit) if meter else None
        self.controls = InverterControls(unit)
        self._group = ComponentGroup(unit, self.components)
        self._info_group = ComponentGroup(
            unit, [inverter.info for inverter in self.inverters]
        )

    @property
    def components(self) -> tuple[Component, ...]:
        """Every subsystem :meth:`async_update` refreshes."""
        optional = (self.weather, self.meter)
        return (
            self.system,
            *(inverter.data for inverter in self.inverters),
            *(component for component in optional if component is not None),
        )

    async def async_update(self) -> None:
        """Refresh every inverter's measurements and the site totals.

        Raises ``BlockReadError`` if the logger rejects a block.
        """
        await self._group.async_update()

    async def async_read_info(self) -> None:
        """Refresh every inverter's identity block.

        These registers are static, so a poller reads them once at setup rather
        than on every cycle.
        """
        await self._info_group.async_update()

    async def async_read_raw(self) -> dict[str, dict[int, int | bool]]:
        """Refresh, and return every polled register word by address.

        The undecoded view of the same read :meth:`async_update` performs — for
        capturing a device dump when a decoded value looks wrong.
        """
        return await self._group.async_read_raw()

    @staticmethod
    async def async_discover(
        unit: ModbusUnit, slots: Sequence[InverterSlot] | None = None
    ) -> tuple[DiscoveredInverter, ...]:
        """Find which of the logger's inverter windows are populated.

        Reads each window's identity block and keeps the ones reporting their own
        Modbus address back, which an empty window does not. That is one request
        per window, so scanning all 90 takes a while — pass ``slots`` to narrow
        it to the ports a site actually uses.

        A window the logger answers with "illegal data address" is skipped: it
        does not serve that part of the map, which is the same news as an empty
        window and should not abandon the rest of the scan. Any other rejection
        is a real fault and raises ``BlockReadError``.
        """
        found = []
        for slot in all_slots() if slots is None else slots:
            info = InverterInfo(unit, base_offset=slot.base_offset)
            try:
                await info.async_update()
            except BlockReadError as err:
                if err.exception_code == ExceptionCode.ILLEGAL_DATA_ADDRESS:
                    continue
                raise
            if info.modbus_address != slot.modbus_id:
                continue
            found.append(
                DiscoveredInverter(
                    slot=slot,
                    serial_number=info.serial_number or "",
                    machine_type=info.machine_type or "",
                )
            )
        return tuple(found)


__all__ = ["AILOGGER_UNIT_ID", "AiLogger", "DiscoveredInverter"]
