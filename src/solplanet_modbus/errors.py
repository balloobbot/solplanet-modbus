"""Inverter error codes for register 1377.

UM0058 defers these to a "section 3.4" that the released V03 manual does not
contain. The table below is transcribed from the AISWEI error codes in
`zbigniewmotyka/home-assistant-solplanet
<https://github.com/zbigniewmotyka/home-assistant-solplanet>`_, which reads the
same inverters through their JSON API and is exercised against real hardware.

That makes this table **unverified against register 1377 itself**: it is the
inverter's own error enumeration, and the logger republishes the inverter's error
register, but nothing in the documentation confirms the two agree. The raw code
stays available as ``InverterData.error_code`` — this only ever adds a label.

Codes the source table marks as reserved are omitted, so an unmapped code reads
as an unknown code rather than as a meaningless label.
"""

from __future__ import annotations

#: Grid-tied inverter error codes.
_PV_ERRORS: dict[int, str] = {
    0: "No error",
    1: "Communication fails between master and slave",
    2: "EEPROM read/write fail",
    3: "Relay check fail",
    4: "DC injection high",
    5: "Auto test function failed",
    6: "DC bus voltage high",
    7: "Internal voltage reference abnormal",
    8: "AC HCT failure",
    9: "GFCI device failure",
    10: "Device fault",
    11: "Master/slave version mismatch",
    32: "ROCOF fault",
    33: "Fac failure: grid frequency out of range",
    34: "AC voltage out of range",
    35: "Utility loss",
    36: "GFCI failure",
    37: "PV over voltage",
    38: "ISO fault",
    39: "Fan lock",
    40: "Over temperature in inverter",
    41: "Consistent fault: Vac differs between master and slave",
    42: "Consistent fault: Fac differs between master and slave",
    43: "Consistent fault: ground current differs between master and slave",
    44: "Consistent fault: DC injection differs between master and slave",
    45: "Consistent fault: Fac and Vac differ between master and slave",
    46: "High DC bus",
    47: "Consistent fault",
    48: "Ten-minute average voltage fault",
    49: "PV1 surge protection device fault",
    50: "PV2 surge protection device fault",
    51: "Fuse fault",
    52: "Missing N fault",
    53: "ISO check: ISO voltage above 300 mV before constant current enabled",
    54: "ISO check: ISO voltage out of range (1.37 V ±20 %) with constant current",
    55: "ISO check: ISO voltage dropped below 40 mV on N/P relay change",
    56: "GFCI protection fault: 30 mA level",
    57: "GFCI protection fault: 60 mA level",
    58: "GFCI protection fault: 150 mA level",
    59: "PV1 string current abnormal",
    60: "PV2 string current abnormal",
    61: "DRMS communication fails (S9 open)",
    62: "DRMS ordered device disconnection (S0 close)",
    63: "L-PE short circuit fault",
    64: "PV input mode error",
    65: "PE connection fault",
    70: "AFCI self-test failed",
    71: "Photovoltaic arcing fault or poor circuit contact",
    305: "Inverter offline",
}

#: Hybrid (storage) inverter error codes.
_HYBRID_ERRORS: dict[int, str] = {
    2000: "Discharge over current",
    2001: "Over load",
    2002: "Battery disconnected",
    2003: "Battery under voltage",
    2004: "Battery low capacity",
    2005: "Battery over voltage",
    2006: "Grid low voltage",
    # The source table repeats "grid low vol" for 2007; kept as transcribed
    # rather than guessed at, since the neighbouring pairs are low/over.
    2007: "Grid low voltage",
    2008: "Grid low frequency",
    2009: "Grid over frequency",
    2010: "GFCI over current",
    2011: "Parallel CAN failure",
    2012: "Grid CT reversed",
    2013: "Bus under voltage",
    2014: "Bus over voltage",
    2015: "Inverter over current",
    2016: "Charge over current",
    2017: "Bus voltage oscillation",
    2018: "Inverter under voltage",
    2019: "Inverter over voltage",
    2020: "Inverter frequency abnormal",
    2021: "IGBT temperature high",
    2023: "Battery over temperature",
    2024: "Battery under temperature",
    2027: "BMS communication failure",
    2028: "Fan failure",
    2030: "Grid phase error",
    2031: "Arc fault",
    2032: "Bus soft-start failure",
    2033: "Inverter soft-start failure",
    2034: "Bus short circuit",
    2035: "Inverter short circuit",
    2037: "PV insulation low",
    2038: "Bus relay fault",
    2039: "Grid relay fault",
    2040: "EPS relay fault",
    2041: "GFCI fault",
    2042: "CT fault",
    2043: "PV short circuit",
    2044: "Bypass relay fault",
    2045: "System fault",
    2046: "Current DC component over limit",
    2047: "Voltage DC component over limit",
}

#: Every known inverter error code, by value.
INVERTER_ERROR_CODES: dict[int, str] = _PV_ERRORS | _HYBRID_ERRORS


def error_description(code: int | None) -> str | None:
    """Describe an inverter error code, or None if it has no known meaning."""
    if code is None:
        return None
    return INVERTER_ERROR_CODES.get(code)
