"""Tests for the RS485-address to register-window mapping (UM0058 section 2.2)."""

from __future__ import annotations

import pytest

from solplanet_modbus import (
    INVERTER_BLOCK_SIZE,
    ComPort,
    UnknownInverterAddressError,
    all_slots,
    port_of,
    slot_for,
    slots_for_port,
)


@pytest.mark.parametrize(
    ("modbus_id", "port", "base_address"),
    [
        # Every boundary of the three tables printed in UM0058 section 2.2.
        (3, ComPort.COM1, 1000),
        (32, ComPort.COM1, 12310),
        (51, ComPort.COM2, 12700),
        (80, ComPort.COM2, 24010),
        (102, ComPort.COM3, 24400),
        (131, ComPort.COM3, 35710),
    ],
)
def test_documented_windows(modbus_id: int, port: ComPort, base_address: int) -> None:
    slot = slot_for(modbus_id)
    assert slot.port is port
    assert slot.base_address == base_address
    assert slot.base_offset == base_address - 1000


def test_windows_are_contiguous_and_end_where_the_totals_start() -> None:
    """90 windows of 390 registers fill 1000-36099, up to the totals at 36100."""
    slots = all_slots()
    assert len(slots) == 90
    assert [slot.window for slot in slots] == list(range(90))
    assert slots[0].base_address == 1000
    assert slots[-1].base_address + INVERTER_BLOCK_SIZE == 36100


@pytest.mark.parametrize("modbus_id", [0, 2, 33, 50, 81, 101, 132, 239])
def test_addresses_outside_the_port_ranges_are_rejected(modbus_id: int) -> None:
    with pytest.raises(UnknownInverterAddressError, match="not in any"):
        slot_for(modbus_id)


def test_port_of_matches_slot_for() -> None:
    assert port_of(51) is ComPort.COM2


def test_slots_for_port() -> None:
    slots = slots_for_port(ComPort.COM3)
    assert len(slots) == 30
    assert [slot.modbus_id for slot in slots] == list(range(102, 132))
    assert ComPort.COM3.first_modbus_id == 102
