"""Map an inverter's RS485 address to its window in the Ai-logger register map.

The logger reserves 90 windows of 390 registers, laid out back to back from
:data:`~solplanet_modbus.const.INVERTER_BASE`: 30 per RS485 port, in port order.
Each port numbers its inverters from a fixed first Modbus address, so the whole
map is described by those three starting addresses.

    COM1  Modbus 3-32     registers 1000-12699
    COM2  Modbus 51-80    registers 12700-24399
    COM3  Modbus 102-131  registers 24400-36099

A window is addressed by shifting the declared 1000-1389 layout, so every
component takes the same field definitions and only its ``base_offset`` differs.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from .const import INVERTER_BASE, INVERTER_BLOCK_SIZE, INVERTERS_PER_PORT
from .exceptions import UnknownInverterAddressError


class ComPort(IntEnum):
    """An RS485 port on the Ai-logger."""

    COM1 = 1
    COM2 = 2
    COM3 = 3

    @property
    def first_modbus_id(self) -> int:
        """The Modbus address the port's first inverter is scanned as."""
        return _FIRST_MODBUS_ID[self]

    @property
    def modbus_ids(self) -> range:
        """Every Modbus address this port can host."""
        first = self.first_modbus_id
        return range(first, first + INVERTERS_PER_PORT)


# Documented per port in UM0058 section 2.2; not a uniform stride, so listed.
_FIRST_MODBUS_ID: dict[ComPort, int] = {
    ComPort.COM1: 3,
    ComPort.COM2: 51,
    ComPort.COM3: 102,
}


@dataclass(frozen=True, slots=True)
class InverterSlot:
    """Where one inverter's data sits in the logger's flat register map."""

    modbus_id: int
    port: ComPort
    #: Position of the window in the map, 0-89.
    window: int

    @property
    def base_address(self) -> int:
        """First register of this inverter's window."""
        return INVERTER_BASE + self.window * INVERTER_BLOCK_SIZE

    @property
    def base_offset(self) -> int:
        """Shift from the declared 1000-1389 layout to this window."""
        return self.window * INVERTER_BLOCK_SIZE


def port_of(modbus_id: int) -> ComPort:
    """The RS485 port an inverter Modbus address belongs to.

    Raises :class:`UnknownInverterAddressError` for an address outside the three
    documented ranges.
    """
    for port in ComPort:
        if modbus_id in port.modbus_ids:
            return port
    ranges = ", ".join(
        f"{port.name} {port.modbus_ids.start}-{port.modbus_ids.stop - 1}"
        for port in ComPort
    )
    raise UnknownInverterAddressError(
        f"Modbus address {modbus_id} is not in any Ai-logger port range ({ranges})"
    )


def slot_for(modbus_id: int) -> InverterSlot:
    """The register window of the inverter scanned at ``modbus_id``.

    Raises :class:`UnknownInverterAddressError` for an unknown address.
    """
    port = port_of(modbus_id)
    window = (port - 1) * INVERTERS_PER_PORT + modbus_id - port.first_modbus_id
    return InverterSlot(modbus_id=modbus_id, port=port, window=window)


def slots_for_port(port: ComPort) -> tuple[InverterSlot, ...]:
    """Every window of one RS485 port, in Modbus address order."""
    return tuple(slot_for(modbus_id) for modbus_id in port.modbus_ids)


def all_slots() -> tuple[InverterSlot, ...]:
    """All 90 windows the logger reserves, in register address order."""
    return tuple(slot for port in ComPort for slot in slots_for_port(port))
