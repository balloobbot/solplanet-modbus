"""Enumerated register values from UM0058 section 2.2.

Codes the document does not enumerate — the grid code (register 1026) and the
error and warning messages (1377, 1378), all of which defer to sections that the
released manual does not contain — stay raw integers on their components.
"""

from __future__ import annotations

from enum import IntEnum


class DeviceState(IntEnum):
    """Inverter operating state (register 1308)."""

    WAIT = 0
    NORMAL = 1
    FAULT = 2
    CHECKING = 4


class FaultState(IntEnum):
    """Whether the inverter reports a fault in itself (register 1376)."""

    NO_INTERNAL_FAULT = 0
    INTERNAL_FAULT = 1


class PhaseType(IntEnum):
    """Inverter phase count (register 1000), transmitted as an ASCII digit."""

    SINGLE_PHASE = 1
    THREE_PHASE = 3


class InverterModel(IntEnum):
    """Inverter model class (register 1072).

    ``PV_*`` are grid-tied models, ``HY_*`` hybrids.
    """

    PV_SINGLE_PHASE_1_3KW = 1
    PV_SINGLE_PHASE_3_6KW = 2
    PV_THREE_PHASE_3_10KW = 3
    PV_THREE_PHASE_15_23KW = 4
    PV_THREE_PHASE_50_60KW = 5
    HY_SINGLE_PHASE_1_3KW = 11
    HY_SINGLE_PHASE_3_6KW = 12
    HY_THREE_PHASE_5_12KW = 13
    HY_SINGLE_PHASE_SUB_1KW = 14  # Compass
    HY_THREE_PHASE_NO_EPS_5_12KW = 15
    HY_THREE_PHASE_DIESEL_5_12KW = 16
