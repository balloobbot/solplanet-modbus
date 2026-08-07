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
