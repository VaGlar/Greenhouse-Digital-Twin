"""Validation tests for twin/params.py's ClimateControlParams.

Covers the sanity checks that previously let physically nonsensical
configs (inverted day/night setpoints, a CO2 day-setpoint below ambient)
through silently -- see api/main.py's ValueError -> 422 handler, which is
what surfaces these as client errors when set via API overrides.
"""

from __future__ import annotations

import pytest

from twin.params import ClimateControlParams


def _params(**overrides):
    defaults = dict(heating_setpoint_day_c=20.0, heating_setpoint_night_c=17.0)
    defaults.update(overrides)
    return ClimateControlParams(**defaults)


def test_accepts_day_setpoint_equal_to_night_setpoint():
    _params(heating_setpoint_day_c=18.0, heating_setpoint_night_c=18.0)


def test_rejects_day_setpoint_below_night_setpoint():
    with pytest.raises(ValueError, match="heating_setpoint_day_c"):
        _params(heating_setpoint_day_c=10.0, heating_setpoint_night_c=30.0)


def test_rejects_negative_co2_ambient_ppm():
    with pytest.raises(ValueError, match="co2_ambient_ppm"):
        _params(co2_ambient_ppm=-10.0)


def test_rejects_co2_day_setpoint_below_ambient():
    with pytest.raises(ValueError, match="co2_setpoint_day_ppm"):
        _params(co2_setpoint_day_ppm=100.0, co2_ambient_ppm=420.0)


def test_accepts_co2_day_setpoint_equal_to_ambient():
    _params(co2_setpoint_day_ppm=420.0, co2_ambient_ppm=420.0)
