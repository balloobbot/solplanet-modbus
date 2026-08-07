"""solplanet-modbus — read a Solplanet (AISWEI) Ai-Logger over Modbus TCP.

The Ai-logger is a Modbus TCP *slave* that polls every inverter on its RS485
ports and republishes their data in one flat input-register map. Point this at a
``ModbusUnit`` bound to unit ID :data:`AILOGGER_UNIT_ID`, say which inverters
the site has, and read the result as normal Python objects::

    logger = AiLogger(unit, modbus_ids=[3, 4], meter=True)
    await logger.async_read_info()
    await logger.async_update()

    logger.inverters[0].info.serial_number
    logger.inverters[0].data.active_power
    logger.system.active_power
    logger.meter.total_power

The library is organized by data map — one module each for ``weather``,
``inverter``, ``meter`` and ``controls`` — built on the generic ``Component`` /
``RegisterField`` framework in ``modbus_connection.model``.
"""

from .addressing import (
    ComPort,
    InverterSlot,
    all_slots,
    port_of,
    slot_for,
    slots_for_port,
)
from .ailogger import AiLogger, DiscoveredInverter
from .const import (
    AILOGGER_UNIT_ID,
    DEFAULT_PORT,
    INVERTER_BASE,
    INVERTER_BLOCK_SIZE,
    INVERTERS_PER_PORT,
    PORT_COUNT,
)
from .controls import ACTIVE_POWER_REFRESH_SECONDS, ControlRegisters, InverterControls
from .enums import DeviceState, FaultState, InverterModel, PhaseType
from .exceptions import (
    SolplanetError,
    SolplanetValueValidationError,
    UnknownInverterAddressError,
)
from .inverter import Inverter, InverterData, InverterInfo, PvInput, PvString
from .meter import EnergyMeter, SystemPower
from .weather import WeatherSensor, WeatherStation

__all__ = [
    "ACTIVE_POWER_REFRESH_SECONDS",
    "AILOGGER_UNIT_ID",
    "DEFAULT_PORT",
    "INVERTERS_PER_PORT",
    "INVERTER_BASE",
    "INVERTER_BLOCK_SIZE",
    "PORT_COUNT",
    "AiLogger",
    "ComPort",
    "ControlRegisters",
    "DeviceState",
    "DiscoveredInverter",
    "EnergyMeter",
    "FaultState",
    "Inverter",
    "InverterControls",
    "InverterData",
    "InverterInfo",
    "InverterModel",
    "InverterSlot",
    "PhaseType",
    "PvInput",
    "PvString",
    "SolplanetError",
    "SolplanetValueValidationError",
    "SystemPower",
    "UnknownInverterAddressError",
    "WeatherSensor",
    "WeatherStation",
    "all_slots",
    "port_of",
    "slot_for",
    "slots_for_port",
]
