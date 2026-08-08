"""Site totals and the SDM630 meter map (UM0058 sections 2.3 and 2.4).

The meter block republishes an Eastron SDM630's own input registers 30001-30081
and 30201-30207 at 36104 and 36186, in that meter's native big-endian IEEE-754
float pairs. The whole meter block spans 102 registers and so still refreshes in
one request, gaps included. It is kept apart from the site totals so a site
without a meter can drop it and keep them.
"""

from __future__ import annotations

from modbus_connection.model import float32, int32

from .const import NAN_S32
from .model import SolplanetComponent


class SystemPower(SolplanetComponent):
    """Summed output of every inverter the logger manages."""

    register_ranges = ((36100, 36103),)

    active_power = int32(36100, nan=NAN_S32, unit="W")
    reactive_power = int32(36102, nan=NAN_S32, unit="var")


class EnergyMeter(SolplanetComponent):
    """An SDM630 meter wired to the logger."""

    register_ranges = ((36104, 36205),)

    l1_voltage = float32(36104, unit="V")
    l2_voltage = float32(36106, unit="V")
    l3_voltage = float32(36108, unit="V")
    l1_current = float32(36110, unit="A")
    l2_current = float32(36112, unit="A")
    l3_current = float32(36114, unit="A")
    l1_power = float32(36116, unit="W")
    l2_power = float32(36118, unit="W")
    l3_power = float32(36120, unit="W")
    l1_apparent_power = float32(36122, unit="VA")
    l2_apparent_power = float32(36124, unit="VA")
    l3_apparent_power = float32(36126, unit="VA")
    l1_reactive_power = float32(36128, unit="var")
    l2_reactive_power = float32(36130, unit="var")
    l3_reactive_power = float32(36132, unit="var")
    l1_power_factor = float32(36134)
    l2_power_factor = float32(36136)
    l3_power_factor = float32(36138)
    l1_phase_angle = float32(36140, unit="°")
    l2_phase_angle = float32(36142, unit="°")
    l3_phase_angle = float32(36144, unit="°")

    average_line_to_neutral_voltage = float32(36146, unit="V")
    average_line_current = float32(36150, unit="A")
    total_line_current = float32(36152, unit="A")
    total_power = float32(36156, unit="W")
    total_apparent_power = float32(36160, unit="VA")
    total_reactive_power = float32(36164, unit="var")
    total_power_factor = float32(36166)
    total_phase_angle = float32(36170, unit="°")
    frequency = float32(36174, unit="Hz")

    # Cumulative since the meter was last reset.
    import_energy = float32(36176, unit="kWh")
    export_energy = float32(36178, unit="kWh")
    import_reactive_energy = float32(36180, unit="kvarh")
    export_reactive_energy = float32(36182, unit="kvarh")
    apparent_energy = float32(36184, unit="kVAh")

    l1_l2_voltage = float32(36186, unit="V")
    l2_l3_voltage = float32(36188, unit="V")
    l3_l1_voltage = float32(36190, unit="V")
    average_line_to_line_voltage = float32(36204, unit="V")
