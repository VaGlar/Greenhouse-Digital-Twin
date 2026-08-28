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


# -- HydroponicParams Level B (EC -> dry matter / BER, damped recipe tier) --


def test_hydroponic_params_rejects_inverted_nutrient_range():
    with pytest.raises(ValueError, match="n_max_optimal_ppm"):
        HydroponicParams(n_min_optimal_ppm=150.0, n_max_optimal_ppm=60.0)


def test_hydroponic_params_rejects_negative_ber_slope():
    with pytest.raises(ValueError, match="ber_yield_loss_fraction_per_ms_cm_above_threshold"):
        HydroponicParams(ber_yield_loss_fraction_per_ms_cm_above_threshold=-0.1)


def test_hydroponic_params_rejects_recipe_adequacy_multiplier_min_of_zero():
    with pytest.raises(ValueError, match="recipe_adequacy_multiplier_min"):
        HydroponicParams(recipe_adequacy_multiplier_min=0.0)


def test_effective_dry_matter_content_fruit_increases_with_ec():
    low = HydroponicParams(ec_target_ms_cm=2.3)
    high = HydroponicParams(ec_target_ms_cm=5.0)
    assert low.effective_dry_matter_content_fruit == pytest.approx(1.0)
    assert high.effective_dry_matter_content_fruit > low.effective_dry_matter_content_fruit


def test_ber_yield_loss_fraction_is_zero_below_threshold():
    params = HydroponicParams(ec_target_ms_cm=3.0, ec_ber_threshold_ms_cm=3.5)
    assert params.ber_yield_loss_fraction == 0.0


def test_ber_yield_loss_fraction_ramps_above_threshold_and_is_capped():
    params = HydroponicParams(
        ec_target_ms_cm=4.5,
        ec_ber_threshold_ms_cm=3.5,
        ber_yield_loss_fraction_per_ms_cm_above_threshold=0.10,
        ber_yield_loss_fraction_max=0.35,
    )
    assert params.ber_yield_loss_fraction == pytest.approx(0.10)

    capped = HydroponicParams(
        ec_target_ms_cm=10.0,
        ec_ber_threshold_ms_cm=3.5,
        ber_yield_loss_fraction_per_ms_cm_above_threshold=0.10,
        ber_yield_loss_fraction_max=0.35,
    )
    assert capped.ber_yield_loss_fraction == 0.35


def test_ec_deficiency_yield_loss_fraction_is_zero_above_threshold():
    params = HydroponicParams(ec_target_ms_cm=3.0, ec_deficiency_threshold_ms_cm=2.0)
    assert params.ec_deficiency_yield_loss_fraction == 0.0


def test_ec_deficiency_yield_loss_fraction_ramps_below_threshold_and_is_capped():
    params = HydroponicParams(
        ec_target_ms_cm=1.0,
        ec_deficiency_threshold_ms_cm=2.0,
        ec_deficiency_yield_loss_fraction_per_ms_cm_below_threshold=0.15,
        ec_deficiency_yield_loss_fraction_max=0.50,
    )
    assert params.ec_deficiency_yield_loss_fraction == pytest.approx(0.15)

    # ec_target_ms_cm must be > 0, so a very high slope (rather than a very low EC) is used to
    # reach the cap within a valid EC value.
    capped = HydroponicParams(
        ec_target_ms_cm=0.01,
        ec_deficiency_threshold_ms_cm=2.0,
        ec_deficiency_yield_loss_fraction_per_ms_cm_below_threshold=10.0,
        ec_deficiency_yield_loss_fraction_max=0.50,
    )
    assert capped.ec_deficiency_yield_loss_fraction == 0.50


def test_ph_availability_multiplier_is_one_when_ph_in_range():
    params = HydroponicParams(ph_target=6.0, ph_min_optimal=5.5, ph_max_optimal=6.5)
    assert params.ph_availability_multiplier == pytest.approx(1.0)


def test_ph_availability_multiplier_drops_when_ph_out_of_range():
    in_range = HydroponicParams(ph_target=6.0)
    out_of_range = HydroponicParams(ph_target=8.0)  # well above ph_max_optimal=6.5
    assert out_of_range.ph_availability_multiplier < in_range.ph_availability_multiplier


def test_ph_availability_multiplier_uses_its_own_higher_cap_than_a_single_nutrient():
    # A pH excursion large enough to hit its individual cap should lose more than any single
    # damped-tier nutrient's cap (ph_availability_penalty_cap_fraction=0.15 vs. 0.02 default).
    far_out = HydroponicParams(ph_target=10.0, ph_min_optimal=5.5, ph_max_optimal=6.5)
    assert far_out.ph_availability_multiplier == pytest.approx(1.0 - 0.15)


def test_recipe_adequacy_multiplier_is_one_when_all_nutrients_in_range():
    params = HydroponicParams(n_ppm=105.0, k_ppm=300.0, mg_ppm=65.0, b_ppm=0.40)
    assert params.recipe_adequacy_multiplier == pytest.approx(1.0)


def test_recipe_adequacy_multiplier_drops_when_a_nutrient_is_out_of_range():
    in_range = HydroponicParams(n_ppm=105.0)
    # n_min_optimal_ppm=60, n_max_optimal_ppm=150 (range width 90) -- one full range-width below
    # the lower boundary reaches the individual penalty cap exactly (0.02).
    out_of_range = HydroponicParams(n_ppm=-30.0)
    assert out_of_range.recipe_adequacy_multiplier < in_range.recipe_adequacy_multiplier
    assert out_of_range.recipe_adequacy_multiplier == pytest.approx(1.0 - 0.02)


def test_recipe_adequacy_multiplier_is_floored_even_with_multiple_out_of_range_nutrients():
    # With all four nutrients far enough out of range to hit their individual penalty cap, and a
    # generously large per-nutrient cap, the combined multiplier would fall below the floor --
    # recipe_adequacy_multiplier_min must clamp it back up.
    params = HydroponicParams(
        n_ppm=-1000.0,
        k_ppm=-1000.0,
        mg_ppm=-1000.0,
        b_ppm=-1000.0,
        damped_nutrient_penalty_cap_fraction=0.5,
        recipe_adequacy_multiplier_min=0.85,
    )
    assert params.recipe_adequacy_multiplier == pytest.approx(0.85)
