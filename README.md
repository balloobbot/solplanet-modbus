# solplanet-modbus

Async Python library for the Modbus TCP interface of **Solplanet (AISWEI) Ai-Logger**
data loggers, built on
[modbus-connection](https://github.com/home-assistant-libs/modbus-connection).

> [!WARNING]
> **Alpha — written from the protocol document, not yet verified against real
> hardware.** Every register address, scale and type is transcribed from
> [UM0058 Ai-logger Modbus TCP V03](docs/UM0058_Ai-logger-Modbus-TCP_EN_V03_0424.pdf)
> (bundled in `docs/`) and covered by tests against an in-memory mock, but no
> physical logger has confirmed them. Expect breaking API changes. Take
> particular care with the **write** operations, which change how every inverter
> on the site behaves. Test reports very welcome.

The Ai-logger is a Modbus TCP **slave**. It polls every inverter on its three
RS485 ports over Modbus RTU and republishes all of their data in one flat
input-register map, so a client talks only to the logger — never to an inverter
directly.

If you have a single inverter with its own WiFi dongle rather than a logger, you
probably want [zbigniewmotyka/home-assistant-solplanet](https://github.com/zbigniewmotyka/home-assistant-solplanet)
instead, which reads the dongle's JSON API directly. This library exists for the
Ai-Logger's Modbus TCP interface, which that integration does not cover — but it
is where the error codes and unimplemented-value sentinels here come from, since
none of that is in the protocol document.

## Design

- It **consumes the connection abstraction**, not a backend: the API takes a
  [`modbus_connection.ModbusUnit`](https://github.com/home-assistant-libs/modbus-connection)
  and reads through it. You choose the backend (tmodbus, pymodbus, …).
- An `AiLogger` is a tree of independently-updatable **components**, each of
  which knows its own registers and refreshes in as few Modbus requests as the
  map allows.
- The site's inverters are **declared, not assumed**. The logger reserves 90
  windows but a site fills a handful, and reading empty ones is pure waste —
  so you name them, or let `AiLogger.async_discover()` find them once at setup.

| Attribute | What |
| --- | --- |
| `inverters[i].info` | serial number, machine type, ratings, firmware and safety versions, MPPT and string counts |
| `inverters[i].data` | state, energy and hour counters, temperatures, per-PV-input and per-string DC, per-phase AC, power and power factor |
| `system` | active and reactive power summed over every inverter |
| `weather` | up to two weather sensors: irradiance, cell and ambient temperatures, humidity, wind |
| `meter` | an SDM630 revenue meter: per-phase and total power, energy counters, frequency |
| `controls` | write-only output power, power factor and on/off commands |

## Installation

```bash
pip install solplanet-modbus
```

## Usage

```python
import asyncio

from modbus_connection.tmodbus import connect_tcp
from solplanet_modbus import AILOGGER_UNIT_ID, DEFAULT_PORT, AiLogger


async def main() -> None:
    connection = await connect_tcp("192.168.1.50", port=DEFAULT_PORT)
    unit = connection.for_unit(AILOGGER_UNIT_ID)

    logger = AiLogger(unit, modbus_ids=[3, 4], meter=True)

    await logger.async_read_info()  # static identity, once at setup
    await logger.async_update()  # measurements, every poll

    for inverter in logger.inverters:
        print(inverter.info.serial_number, inverter.info.machine_type)
        print(" state:", inverter.data.state, inverter.data.error_description)
        print(" power:", inverter.data.active_power, "W")
        print(" today:", inverter.data.energy_today, "kWh")
        print(" PV:", inverter.data.pv_voltages[:2], inverter.data.pv_currents[:2])

    print("site total:", logger.system.active_power, "W")
    print("meter:", logger.meter.total_power, "W")

    await connection.close()


asyncio.run(main())
```

### Finding the inverters

`async_discover()` reads each reserved window and keeps the ones that report
their own RS485 address back. A window the logger rejects as an illegal data
address is skipped rather than abandoning the scan. Narrow it to the ports the
site uses — a full scan is 90 requests:

```python
from solplanet_modbus import AiLogger, ComPort, slots_for_port

found = await AiLogger.async_discover(unit, slots_for_port(ComPort.COM1))
logger = AiLogger(unit, [inverter.modbus_id for inverter in found])
```

There is a command-line tool for the same thing:

```bash
uv run --extra cli python script/query.py 192.168.1.50 --discover --meter
```

## Addressing

UM0058 documents two ways to reach an inverter, and this library supports both.

**Method 1** — unit ID `239`, always available. Every inverter gets its own
390-register window in one flat map, laid out per RS485 port:

| Port | Modbus addresses | Registers |
| --- | --- | --- |
| COM1 | 3–32 | 1000–12699 |
| COM2 | 51–80 | 12700–24399 |
| COM3 | 102–131 | 24400–36099 |

This is what `AiLogger` uses: it takes one unit and shifts each inverter's
fields to its own window.

**Method 2** — firmware 006R and above. The unit ID *is* the inverter's RS485
address and its data always sits at 1000–1389. Build an `Inverter` directly
against a unit bound to that address:

```python
from solplanet_modbus import Inverter

inverter = Inverter(connection.for_unit(3))  # method 2: unit ID = RS485 address
await inverter.async_update_info()
await inverter.async_update()
```

Method 2 is also the only mode in which the logger passes reads and writes
through to an inverter's own 4X registers. Those registers belong to the AISWEI
inverter protocol rather than to UM0058, so they are not modelled here.

## Controlling output power

The control registers are **write-only**, and a write applies to *every* inverter
the logger manages — there is no per-inverter control register.

```python
await logger.controls.async_set_active_power_limit(80)  # cap at 80 % of rated
await logger.controls.async_set_power_factor(0.95)  # leading
await logger.controls.async_turn_off()
```

`async_adjust_active_power()` is different from the rest and easy to misuse: it
is a **relative adjustment**, not a setpoint. UM0058's own example takes a 100 kW
inverter producing 30 kW to 50 kW by writing `20` — the delta as a percentage of
*rated* power. The logger holds it briefly, so a controller must rewrite it about
every 500 ms for as long as it should apply.

## Notes from the protocol document

Things worth knowing before pointing this at a real logger:

- **Only one master at a time.** The logger serves a single Modbus TCP client.
- **Keep polling.** UM0058 asks for a request every 1–3 seconds; after a
  disconnect or timeout, reconnect no sooner than 5 seconds later. For a one-off
  read, close the connection when done.
- **The logger's own poll rate bounds yours.** It reads each inverter about
  every 5 seconds, in turn, so polling faster than that returns the same values.
- **Port 9999 by default**, changeable to 502 or any port in 1024–20000 from the
  web interface (System settings → Communication settings → Network settings).

### Gaps and errata in UM0058

The document promises three code tables it does not contain: the **grid code**
(register 1026, "section 3.5") and the **error and warning codes** (registers
1377 and 1378, "section 3.4"). Neither section exists in the released V03 manual.

The error codes are filled in anyway — see *Where the undocumented parts come
from* below. The grid code and the warning code stay raw integers.

Two printed addresses are typos, corrected here: PV7 voltage as `31330` (it is
1330) and the slave CPU sub-version range as `1103~1015` (it is 1103–1105).

The document also never says what an inverter reports for a register it does not
implement. It is the usual AISWEI convention — all ones for an unsigned type,
the sign bit alone for a signed one — so every numeric field carries that
sentinel and decodes it to `None`:

| Type | Unimplemented |
| --- | --- |
| U16 / E16 | `0xFFFF` |
| S16 | `0x8000` |
| U32 | `0xFFFFFFFF` |
| S32 | `0x80000000` |

Without this, a single-phase inverter's absent L3 voltage reads as 6553.5 V and a
missing temperature probe as −3276.8 °C. Note that the sentinel is matched on the
raw word, so a genuine −1 W stays −1 W.

### Where the undocumented parts come from

The error code table and the sentinel values are transcribed from
[zbigniewmotyka/home-assistant-solplanet](https://github.com/zbigniewmotyka/home-assistant-solplanet),
which reads the same inverters through their JSON API and is exercised against
real hardware. That integration independently confirms every scaling factor this
library derives from UM0058 — frequency ×0.01, energy ×0.1 kWh, temperature
×0.1 °C, voltage ×0.1 V, power ×1 — and its inverter status codes match the
document's exactly.

Two caveats. The error table is the *inverter's* enumeration, reached over a
different transport; nothing confirms register 1377 uses the same numbering, so
`error_code` keeps the raw value and `error_description` only ever adds a label.
And codes that table marks reserved are omitted here, so an unmapped code reads
as unknown rather than as a meaningless string.

Register 986's wind speed is documented with no gain but a maximum of 6000,
which only makes sense at a 0.01 scale. It is exposed unscaled as
`wind_speed_raw` so the document and the library agree; divide by 100 if a real
sensor reads high.

## Development

```bash
uv sync
uv run pytest
uv run mypy src tests script/query.py
uvx ruff format . && uvx ruff check .
```

Tests run against the in-memory mock backend that ships with `modbus-connection`,
so no hardware, server or socket is involved.

## License

Apache-2.0. UM0058 is redistributed in `docs/` as the protocol reference this
library implements; it remains the property of AISWEI Technology Co., Ltd.
