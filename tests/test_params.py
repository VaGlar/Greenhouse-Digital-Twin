"""Validation tests for twin/params.py's ClimateControlParams.

Covers the sanity checks that previously let physically nonsensical
configs (inverted day/night setpoints, a CO2 day-setpoint below ambient)
through silently -- see api/main.py's ValueError -> 422 handler, which is
what surfaces these as client errors when set via API overrides.
"""

from __future__ import annotations

import pytest

from twin.params import ClimateControlParams, HydroponicParams


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


# -- HydroponicParams (hydroponics.md Level A) --


def test_hydroponic_params_rejects_zero_ec_target():
    with pytest.raises(ValueError, match="ec_target_ms_cm"):
        HydroponicParams(ec_target_ms_cm=0.0)


def test_hydroponic_params_rejects_ph_target_out_of_range():
    with pytest.raises(ValueError, match="ph_target"):
        HydroponicParams(ph_target=14.0)


def test_hydroponic_params_rejects_drainage_fraction_of_one():
    with pytest.raises(ValueError, match="drainage_target_fraction"):
        HydroponicParams(drainage_target_fraction=1.0)


def test_hydroponic_params_rejects_zero_pump_specific_power():
    with pytest.raises(ValueError, match="irrigation_pump_specific_power_kwh_per_m3"):
        HydroponicParams(irrigation_pump_specific_power_kwh_per_m3=0.0)


def test_hydroponic_params_rejects_zero_fertilizer_conversion_factor():
    with pytest.raises(ValueError, match="fertilizer_g_per_l_per_ec_unit"):
        HydroponicParams(fertilizer_g_per_l_per_ec_unit=0.0)
