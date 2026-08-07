"""Inverter output power control (UM0058 section 2.5).

These are the only holding registers UM0058 documents, they are write-only, and
a write applies to *every* inverter the logger manages — there is no per-inverter
control register. They are therefore never polled: the values here cannot be
read back, and the effect of a write shows up in the inverters' measurements.

The document notes two timing requirements for a controller driving these: the
fast active power command must be rewritten every 500 ms to stay in effect, and
the Modbus TCP link must be exercised every 1-3 s or the logger drops it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from modbus_connection.model import gauge, integer

from .model import SolplanetControlComponent, bounded

if TYPE_CHECKING:
    from modbus_connection import ModbusUnit

#: How often the active power adjustment must be rewritten to stay in effect.
ACTIVE_POWER_REFRESH_SECONDS = 0.5

_ON = 1
_OFF = 2


class ControlRegisters(SolplanetControlComponent):
    """The five write-only control registers."""

    # A *relative* adjustment, not a setpoint: UM0058's own worked example writes
    # (target - current) / rated * 100, so raising a 100 kW inverter from 30 kW
    # to 50 kW is +20. See InverterControls.async_adjust_active_power.
    active_power_adjustment = gauge(60000, 0.01, writable=bounded(-100, 100), unit="%")
    power_factor = gauge(60001, 0.0001, writable=bounded(-1, 1, excluded=(-0.75, 0.75)))
    on_off = integer(60002, signed=False, writable=bounded(_ON, _OFF))
    active_power_limit = gauge(
        60003, 0.01, signed=False, writable=bounded(0, 110), unit="%"
    )
    reactive_power = gauge(60004, 0.01, writable=bounded(-65, 65), unit="%")


class InverterControls:
    """Write-only commands the logger forwards to every inverter it manages."""

    def __init__(self, unit: ModbusUnit) -> None:
        self._registers = ControlRegisters(unit)

    async def async_adjust_active_power(self, percent: float) -> None:
        """Adjust active output power by ``percent`` of rated power, -100 to 100.

        This is a delta against what the inverters are producing now, not a
        target: to take a 100 kW inverter from 30 kW to 50 kW, pass ``20``.
        Pass ``-100`` to drive output to zero. The logger holds the adjustment
        for a short while only — rewrite it every
        :data:`ACTIVE_POWER_REFRESH_SECONDS` for as long as it should apply.
        """
        await self._registers.write("active_power_adjustment", percent)

    async def async_set_active_power_limit(self, percent: float) -> None:
        """Cap active output power at ``percent`` of rated power, 0 to 110."""
        await self._registers.write("active_power_limit", percent)

    async def async_set_power_factor(self, power_factor: float) -> None:
        """Set the AC power factor: 0.75 to 1 leading, -1 to -0.75 lagging.

        Raises
        :class:`~solplanet_modbus.exceptions.SolplanetValueValidationError` for
        a value in the unusable band between the two.
        """
        await self._registers.write("power_factor", power_factor)

    async def async_set_reactive_power(self, percent: float) -> None:
        """Set reactive power to ``percent`` of rated apparent power.

        0 to 65 is leading, -65 to 0 lagging.
        """
        await self._registers.write("reactive_power", percent)

    async def async_turn_on(self) -> None:
        """Turn the inverters on."""
        await self._registers.write("on_off", _ON)

    async def async_turn_off(self) -> None:
        """Turn the inverters off."""
        await self._registers.write("on_off", _OFF)
