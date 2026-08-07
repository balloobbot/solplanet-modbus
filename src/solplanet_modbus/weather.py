"""Weather station data (UM0058 section 2.1).

The logger maps two identically shaped sensors back to back, 986-992 and
993-999. They are modelled as one station covering both, so a refresh is a
single read; a site with one sensor simply leaves the second reading zeros.
"""

from __future__ import annotations

from modbus_connection.model import gauge, integer, repeating_group

from .model import SolplanetComponent

#: Registers per weather sensor.
SENSOR_STRIDE = 7

#: Weather sensors the logger maps.
SENSOR_COUNT = 2


class WeatherSensor(SolplanetComponent):
    """One weather station sensor.

    Declares no readable range of its own: its addresses are read as part of the
    :class:`WeatherStation` block it belongs to.
    """

    # UM0058 documents no gain here but bounds the raw value at 6000, which only
    # makes sense as a wind speed at a 0.01 scale (0-60 m/s). The value is left
    # unscaled to match the document; divide by 100 if the sensor reads high.
    wind_speed_raw = integer(986, signed=False, unit="m/s")
    irradiance = gauge(987, 0.1, signed=False, unit="W/m²")
    cell_temperature = gauge(988, 0.1, unit="°C")
    external_temperature_1 = gauge(989, 0.1, unit="°C")
    external_temperature_2 = gauge(990, 0.1, unit="°C")
    humidity = integer(991, signed=False, unit="%")
    wind_direction = integer(992, signed=False, unit="°")


class WeatherStation(SolplanetComponent):
    """Both weather sensors the logger maps."""

    register_ranges = ((986, 999),)

    sensors = repeating_group(SENSOR_COUNT, WeatherSensor, stride=SENSOR_STRIDE)
