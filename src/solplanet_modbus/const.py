"""Protocol constants from UM0058 (Ai-logger Modbus TCP, V03).

Address values here are stated in the *declared* coordinates the components use:
the first inverter window (COM1, Modbus address 3) at 1000-1389. Every other
window is the same layout shifted by a ``base_offset`` — see :mod:`addressing`.
"""

from __future__ import annotations

from typing import Final

#: The Ai-logger's factory default Modbus TCP port. The web interface can switch
#: it to the standard 502 or to any user-defined port in 1024-20000.
DEFAULT_PORT: Final = 9999

#: Slave ID for "method 1" addressing, where every inverter has its own window in
#: one flat register map. Always available. Inverter 4X register access is not
#: supported through this ID.
AILOGGER_UNIT_ID: Final = 239

#: Registers reserved per inverter window, whether or not the inverter uses them.
INVERTER_BLOCK_SIZE: Final = 390

#: First register of the COM1 / address 3 window, the coordinates the inverter
#: components declare their fields in.
INVERTER_BASE: Final = 1000

#: Inverters attached per RS485 port, and the number of ports.
INVERTERS_PER_PORT: Final = 30
PORT_COUNT: Final = 3

# UM0058 documents no sentinel for a register an inverter does not implement,
# but the wider AISWEI Modbus protocol marks one with the all-ones pattern for an
# unsigned type and the sign bit alone for a signed one. Fields carry these so an
# unimplemented register decodes to None instead of to 6553.5 V or -3276.8 °C.
# Taken from the AISWEI RTU codec in zbigniewmotyka/home-assistant-solplanet,
# which is exercised against real inverters.
NAN_U16: Final = 0xFFFF
NAN_S16: Final = 0x8000
NAN_U32: Final = 0xFFFFFFFF
NAN_S32: Final = 0x80000000
#: The same for an ``E16`` number code, which the protocol treats as unsigned.
NAN_E16: Final = 0xFFFF
