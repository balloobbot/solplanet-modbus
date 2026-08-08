#!/usr/bin/env python3
"""Query a Solplanet Ai-logger over Modbus TCP and print every value.

Reads the logger once and dumps each inverter's identity and measurements, the
site totals and — when asked for — the weather station and SDM630 meter. Handy
for checking a real logger without Home Assistant.

The library only needs the connection *protocol*; the backend comes from the
``cli`` extra::

    uv run --extra cli python script/query.py 192.168.1.50 --discover
    uv run --extra cli python script/query.py 192.168.1.50 --inverter 3 --inverter 4

The logger is a Modbus TCP slave speaking native TCP framing on port 9999 by
default, and accepts only one master at a time — close anything else polling it
first.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time

from modbus_connection import ModbusError
from modbus_connection.cli_helper import (
    CountingUnit,
    add_connection_args,
    connect_from_args,
    print_component,
)

from solplanet_modbus import (
    AILOGGER_UNIT_ID,
    DEFAULT_PORT,
    AiLogger,
    ComPort,
    slots_for_port,
)

# The logger only serves native Modbus TCP; it is not a serial bridge.
CONNECTIONS: tuple[tuple[str, str | None], ...] = (("tcp", "socket"),)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        epilog=(
            f"Defaults suit an Ai-logger: port {DEFAULT_PORT} and unit ID "
            f"{AILOGGER_UNIT_ID}, the ID that carries every inverter at its own "
            "register window."
        ),
    )
    group = add_connection_args(parser, connections=CONNECTIONS)
    group.add_argument(
        "--unit",
        type=int,
        default=AILOGGER_UNIT_ID,
        help=f"Modbus unit/station address (default: {AILOGGER_UNIT_ID})",
    )
    parser.set_defaults(framer="socket", port=DEFAULT_PORT)
    parser.add_argument(
        "--inverter",
        type=int,
        action="append",
        default=[],
        metavar="MODBUS_ID",
        dest="inverters",
        help="RS485 address of an inverter to read; repeatable",
    )
    parser.add_argument(
        "--discover",
        action="store_true",
        help="scan for populated inverter windows instead of naming them",
    )
    parser.add_argument(
        "--port-scan",
        type=int,
        choices=[port.value for port in ComPort],
        action="append",
        default=[],
        metavar="COM",
        dest="scan_ports",
        help="limit --discover to this RS485 port (1-3); repeatable",
    )
    parser.add_argument(
        "--weather", action="store_true", help="also read the weather station"
    )
    parser.add_argument(
        "--meter", action="store_true", help="also read the SDM630 meter"
    )
    args = parser.parse_args(argv)
    if not args.inverters and not args.discover:
        parser.error("name at least one --inverter, or pass --discover")
    return args


async def _discover(unit: CountingUnit, args: argparse.Namespace) -> list[int]:
    slots = None
    if args.scan_ports:
        slots = [
            slot for com in args.scan_ports for slot in slots_for_port(ComPort(com))
        ]
    found = await AiLogger.async_discover(unit, slots)
    for inverter in found:
        print(
            f"  {inverter.slot.port.name} address {inverter.modbus_id}: "
            f"{inverter.machine_type} {inverter.serial_number}"
        )
    return [inverter.modbus_id for inverter in found]


def _print(logger: AiLogger) -> None:
    for inverter in logger.inverters:
        assert inverter.slot is not None  # AiLogger always addresses by window
        label = f"Inverter {inverter.slot.modbus_id}"
        print()
        print_component(inverter.info, title=f"{label} — identity")
        print()
        print_component(inverter.data, title=f"{label} — measurements")
    print()
    print_component(logger.system, title="Site totals")
    if logger.weather is not None:
        print()
        # print_component renders the station's two sensors as sub-blocks.
        print_component(logger.weather, title="Weather station")
    if logger.meter is not None:
        print()
        print_component(logger.meter, title="Energy meter")


async def _run(args: argparse.Namespace) -> int:
    # Requests would connect on demand, but connecting up front reports an
    # unreachable logger as a connection failure rather than a failed read.
    try:
        connection = await connect_from_args(args)
    except ModbusError as err:
        print(f"Could not connect: {err}", file=sys.stderr)
        return 1
    unit = CountingUnit(connection.for_unit(args.unit))
    try:
        modbus_ids = list(args.inverters)
        if args.discover:
            print("Scanning for inverters...")
            modbus_ids += [
                modbus_id
                for modbus_id in await _discover(unit, args)
                if modbus_id not in modbus_ids
            ]
            if not modbus_ids:
                print("No inverters found.", file=sys.stderr)
                return 1
        logger = AiLogger(unit, modbus_ids, weather=args.weather, meter=args.meter)
        start = time.monotonic()
        await logger.async_read_info()
        await logger.async_update()
        elapsed = time.monotonic() - start
    except ModbusError as err:
        print(f"Error reading logger: {err}", file=sys.stderr)
        return 1
    finally:
        # close() is permanent — the right end for a one-shot query.
        await connection.close()
    _print(logger)
    print(f"\nQueried in {elapsed * 1000:.0f} ms ({unit.reads} Modbus reads)")
    return 0


def main() -> int:
    return asyncio.run(_run(_parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
