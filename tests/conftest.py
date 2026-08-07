"""Fixtures: an Ai-logger over modbus-connection's in-memory mock backend.

The mock backend (and its ``mock_modbus_unit`` fixture) ship with
``modbus-connection`` as an auto-registered pytest plugin, so there is no real
server, socket, or backend here — just an address-keyed store loaded with values
shaped like the register dumps in UM0058.

The site modelled below is two three-phase inverters, one on each of the first
two RS485 ports, plus a weather station and an SDM630 meter.
"""

from __future__ import annotations

import struct

import pytest
from modbus_connection.mock import MockModbusUnit

from solplanet_modbus import AiLogger, slot_for

#: The inverters the fixture populates, by RS485 address.
INVERTER_IDS = (3, 51)


def words_for_string(text: str, length: int) -> dict[int, int]:
    """Encode ``text`` as ``length`` null-padded big-endian register words."""
    raw = text.encode("ascii").ljust(length * 2, b"\x00")
    return {i: (raw[i * 2] << 8) | raw[i * 2 + 1] for i in range(length)}


def words_for_float(value: float) -> tuple[int, int]:
    """Encode ``value`` as an SDM630 big-endian IEEE-754 register pair."""
    high, low = struct.unpack(">HH", struct.pack(">f", value))
    return high, low


def _relative(offsets: dict[int, int], base: int) -> dict[int, int]:
    return {base + address: value for address, value in offsets.items()}


def inverter_registers(
    modbus_id: int, serial: str, energy_today: int
) -> dict[int, int]:
    """Registers of one inverter window, keyed by absolute address.

    Values are decoded inline; the identity block is at 1000-1123 of the window
    and the measurements at 1300-1388.
    """
    offsets: dict[int, int] = {
        1000: 0x0033,  # device type, an ASCII '3' -> three phase
        1001: modbus_id,
        1026: 14,  # grid code, an opaque number without the missing section 3.5
        1027: 0,  # rated power high word -> 20000 W
        1028: 20000,
        1072: 3,  # model -> PV_THREE_PHASE_3_10KW
        1073: 2,  # MPPT count
        1074: 4,  # string current count
        1116: 2,  # strings on PV1-4
        1117: 2,  # strings on PV5-8
        1118: 0,
        1119: 0,
        1120: 0,
        1121: 0,
        1122: 0,
        1123: 0,
        1300: 2300,  # grid rated voltage -> 230.0 V
        1301: 5000,  # grid rated frequency -> 50.00 Hz
        1302: 0,  # E-today high word
        1303: energy_today,
        1304: 1,  # E-total -> (65536 + 4464) / 10 = 7000.0 kWh
        1305: 4464,
        1306: 0,  # H-total -> 8760 h
        1307: 8760,
        1308: 1,  # state -> NORMAL
        1309: 342,  # connect time, seconds
        1310: 415,  # internal temperature -> 41.5 °C
        1311: 380,
        1312: 385,
        1313: 390,
        1314: 402,
        1315: 0,  # no bidirectional DC/DC converter on a PV inverter
        1316: 6500,  # bus voltage -> 650.0 V
        1318: 3450,  # PV1 -> 345.0 V
        1319: 512,  # PV1 -> 5.12 A
        1320: 3380,  # PV2 -> 338.0 V
        1321: 498,  # PV2 -> 4.98 A
        1338: 256,  # string 1 -> 25.6 A
        1339: 261,  # string 2 -> 26.1 A
        1358: 2312,  # L1 -> 231.2 V
        1359: 78,  # L1 -> 7.8 A
        1360: 2298,
        1361: 76,
        1362: 2305,
        1363: 77,
        1364: 3998,  # RS line voltage -> 399.8 V
        1365: 4001,
        1366: 3995,
        1367: 5001,  # grid frequency -> 50.01 Hz
        1368: 0,  # apparent power -> 5400 VA
        1369: 5400,
        1370: 0,  # active power -> 5389 W
        1371: 5389,
        1372: 0xFFFF,  # reactive power -> -120 var
        1373: 0x10000 - 120,
        1374: 99,  # power factor -> 0.99
        1376: 0,  # fault state -> NO_INTERNAL_FAULT
        1377: 0,
        1378: 0,
        1388: 7,
    }
    offsets |= {1002 + i: w for i, w in words_for_string(serial, 16).items()}
    offsets |= {1018 + i: w for i, w in words_for_string("ASW8000", 8).items()}
    offsets |= {1029 + i: w for i, w in words_for_string("V1.0.5", 7).items()}
    offsets |= {1036 + i: w for i, w in words_for_string("V1.0.3", 7).items()}
    offsets |= {1043 + i: w for i, w in words_for_string("VDE4105", 7).items()}
    offsets |= {1050 + i: w for i, w in words_for_string("2.1.5", 6).items()}
    offsets |= {1056 + i: w for i, w in words_for_string("AISWEI", 8).items()}
    offsets |= {1064 + i: w for i, w in words_for_string("AISWEI", 8).items()}
    offsets |= {1075 + i: w for i, w in words_for_string("H2", 2).items()}
    offsets |= {1077 + i: w for i, w in words_for_string("A01", 3).items()}
    offsets |= {1096 + i: w for i, w in words_for_string("V1.0.3", 7).items()}
    offsets |= {1103 + i: w for i, w in words_for_string("B02", 3).items()}
    return _relative(offsets, slot_for(modbus_id).base_offset)


#: Weather station, both sensors (986-999).
WEATHER: dict[int, int] = {
    986: 42,  # wind speed, unscaled per UM0058
    987: 8123,  # irradiance -> 812.3 W/m²
    988: 315,  # cell temperature -> 31.5 °C
    989: 224,  # external temperature 1 -> 22.4 °C
    990: 0xFFFF - 54,  # external temperature 2 -> -5.5 °C
    991: 47,  # humidity, %
    992: 178,  # wind direction, degrees
    993: 38,
    994: 8090,
    995: 250,
    996: 220,
    997: 0,
    998: 45,
    999: 180,
}

#: Site totals (36100-36103): the two inverters summed.
SYSTEM: dict[int, int] = {
    36100: 0,
    36101: 10778,  # active power -> 10778 W
    36102: 0xFFFF,
    36103: 0x10000 - 240,  # reactive power -> -240 var
}

#: SDM630 meter, big-endian float pairs (36104-36205).
_METER_VALUES: dict[int, float] = {
    36104: 238.7,
    36106: 239.1,
    36108: 237.9,
    36110: 6.05,
    36112: 6.11,
    36114: 5.98,
    36116: -1444.5,
    36118: -1460.9,
    36120: -1422.6,
    36122: 1444.6,
    36124: 1461.0,
    36126: 1422.7,
    36128: 12.5,
    36130: 12.7,
    36132: 12.1,
    36134: 0.99,
    36136: 0.99,
    36138: 0.98,
    36140: 1.2,
    36142: 1.3,
    36144: 1.4,
    36146: 238.57,
    36150: 6.05,
    36152: 18.14,
    36156: -4328.0,
    36160: 4328.3,
    36164: 37.3,
    36166: 0.99,
    36170: 1.3,
    36174: 50.01,
    36176: 1234.5,
    36178: 8765.4,
    36180: 12.3,
    36182: 45.6,
    36184: 8900.1,
    36186: 413.4,
    36188: 414.1,
    36190: 412.8,
    36204: 413.43,
}

METER: dict[int, int] = {
    address + offset: word
    for address, value in _METER_VALUES.items()
    for offset, word in enumerate(words_for_float(value))
}

#: The whole input-register map the fixtures load.
INPUT: dict[int, int] = {
    **inverter_registers(3, "QA10010022920081", 1234),
    **inverter_registers(51, "QA10010022920082", 987),
    **WEATHER,
    **SYSTEM,
    **METER,
}


@pytest.fixture
def unit(mock_modbus_unit: MockModbusUnit) -> MockModbusUnit:
    """The mock unit, preloaded with the modelled site's registers."""
    mock_modbus_unit.input.update(INPUT)
    return mock_modbus_unit


@pytest.fixture
def logger(unit: MockModbusUnit) -> AiLogger:
    """An Ai-logger reading both inverters, the weather station and the meter."""
    return AiLogger(unit, INVERTER_IDS, weather=True, meter=True)
