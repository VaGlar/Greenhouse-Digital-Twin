"""Validation tests for twin/params.py's ClimateControlParams.

Covers the sanity checks that previously let physically nonsensical
configs (inverted day/night setpoints, a CO2 day-setpoint below ambient)
through silently -- see api/main.py's ValueError -> 422 handler, which is
what surfaces these as client errors when set via API overrides.
"""

from __future__ import annotations

import pytest

from twin.params import ClimateControlParams, ClimatePhase, HydroponicParams


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


# -- Phase-aware climate control, temperature (docs/plans/2026-08-31-phase-aware-climate-design.md) --


def test_heating_setpoint_ignores_deltas_during_vegetative_phase():
    params = _params(
        ramp_up_heating_setpoint_day_delta_c=5.0,
        ramp_up_heating_setpoint_night_delta_c=5.0,
        full_fruiting_heating_setpoint_day_delta_c=5.0,
        full_fruiting_heating_setpoint_night_delta_c=5.0,
    )
    assert params.heating_setpoint(hour=12, phase=ClimatePhase.VEGETATIVE) == 20.0
    assert params.heating_setpoint(hour=2, phase=ClimatePhase.VEGETATIVE) == 17.0


def test_heating_setpoint_applies_ramp_up_delta():
    params = _params(
        ramp_up_heating_setpoint_day_delta_c=1.5,
        ramp_up_heating_setpoint_night_delta_c=-0.5,
    )
    assert params.heating_setpoint(hour=12, phase=ClimatePhase.RAMP_UP) == pytest.approx(21.5)
    assert params.heating_setpoint(hour=2, phase=ClimatePhase.RAMP_UP) == pytest.approx(16.5)


def test_heating_setpoint_applies_full_fruiting_delta():
    params = _params(
        full_fruiting_heating_setpoint_day_delta_c=2.0,
        full_fruiting_heating_setpoint_night_delta_c=2.0,
    )
    assert params.heating_setpoint(hour=12, phase=ClimatePhase.FULL_FRUITING) == pytest.approx(22.0)
    assert params.heating_setpoint(hour=2, phase=ClimatePhase.FULL_FRUITING) == pytest.approx(19.0)


def test_overriding_baseline_shifts_every_phase_equally():
    # The whole point of the baseline+delta design: one override changes the vegetative baseline,
    # which shifts ramp_up/full_fruiting targets by the same amount since they're defined
    # relative to it -- no separate per-phase overrides needed.
    base = _params(full_fruiting_heating_setpoint_day_delta_c=2.0)
    warmer = _params(heating_setpoint_day_c=25.0, full_fruiting_heating_setpoint_day_delta_c=2.0)

    base_full = base.heating_setpoint(hour=12, phase=ClimatePhase.FULL_FRUITING)
    warmer_full = warmer.heating_setpoint(hour=12, phase=ClimatePhase.FULL_FRUITING)
    assert warmer_full - base_full == pytest.approx(25.0 - 20.0)


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


def test_hydroponic_params_rejects_negative_ec_high_side_curvature():
    with pytest.raises(ValueError, match="ec_high_side_curvature_per_ms_cm2"):
        HydroponicParams(ec_high_side_curvature_per_ms_cm2=-0.1)


def test_hydroponic_params_rejects_recipe_adequacy_multiplier_min_of_zero():
    with pytest.raises(ValueError, match="recipe_adequacy_multiplier_min"):
        HydroponicParams(recipe_adequacy_multiplier_min=0.0)


def test_effective_dry_matter_content_fruit_increases_with_ec():
    low = HydroponicParams(ec_target_ms_cm=2.3)
    high = HydroponicParams(ec_target_ms_cm=5.0)
    assert low.effective_dry_matter_content_fruit == pytest.approx(1.0)
    assert high.effective_dry_matter_content_fruit > low.effective_dry_matter_content_fruit


def test_ber_yield_loss_fraction_is_zero_at_and_below_optimal():
    at_peak = HydroponicParams(ec_target_ms_cm=3.0, ec_optimal_ms_cm=3.0)
    below_peak = HydroponicParams(ec_target_ms_cm=1.0, ec_optimal_ms_cm=3.0)
    assert at_peak.ber_yield_loss_fraction == 0.0
    assert below_peak.ber_yield_loss_fraction == 0.0


def test_ber_yield_loss_fraction_grows_continuously_above_optimal_and_is_capped():
    params = HydroponicParams(
        ec_target_ms_cm=4.5,
        ec_optimal_ms_cm=3.0,
        ec_high_side_curvature_per_ms_cm2=0.0444,
        ber_yield_loss_fraction_max=0.35,
    )
    assert params.ber_yield_loss_fraction == pytest.approx(0.0444 * 1.5**2)

    capped = HydroponicParams(
        ec_target_ms_cm=20.0,
        ec_optimal_ms_cm=3.0,
        ec_high_side_curvature_per_ms_cm2=0.0444,
        ber_yield_loss_fraction_max=0.35,
    )
    assert capped.ber_yield_loss_fraction == 0.35


def test_ec_deficiency_yield_loss_fraction_is_zero_at_and_above_optimal():
    at_peak = HydroponicParams(ec_target_ms_cm=3.0, ec_optimal_ms_cm=3.0)
    above_peak = HydroponicParams(ec_target_ms_cm=5.0, ec_optimal_ms_cm=3.0)
    assert at_peak.ec_deficiency_yield_loss_fraction == 0.0
    assert above_peak.ec_deficiency_yield_loss_fraction == 0.0


def test_ec_deficiency_yield_loss_fraction_grows_continuously_below_optimal_and_is_capped():
    params = HydroponicParams(
        ec_target_ms_cm=1.0,
        ec_optimal_ms_cm=3.0,
        ec_low_side_curvature_per_ms_cm2=0.0375,
        ec_deficiency_yield_loss_fraction_max=0.50,
    )
    assert params.ec_deficiency_yield_loss_fraction == pytest.approx(0.0375 * 2.0**2)

    capped = HydroponicParams(
        ec_target_ms_cm=0.01,
        ec_optimal_ms_cm=3.0,
        ec_low_side_curvature_per_ms_cm2=10.0,
        ec_deficiency_yield_loss_fraction_max=0.50,
    )
    assert capped.ec_deficiency_yield_loss_fraction == 0.50


def test_ec_yield_response_has_no_flat_zone_around_the_peak():
    # The whole point of the continuous-bell redesign: two EC values on the same side of the
    # peak, both inside the old "commercial target range", must still differ -- unlike the
    # earlier flat-plateau version.
    near_peak = HydroponicParams(ec_target_ms_cm=3.0)
    slightly_off = HydroponicParams(ec_target_ms_cm=3.3)
    assert slightly_off.ber_yield_loss_fraction > near_peak.ber_yield_loss_fraction


def test_ph_availability_multiplier_is_one_only_exactly_at_the_optimum():
    at_optimum = HydroponicParams(ph_target=5.5, ph_optimal=5.5)
    assert at_optimum.ph_availability_multiplier == pytest.approx(1.0)


def test_ph_availability_multiplier_drops_continuously_on_both_sides_of_the_optimum():
    at_optimum = HydroponicParams(ph_target=5.5, ph_optimal=5.5)
    below = HydroponicParams(ph_target=5.0, ph_optimal=5.5)
    above = HydroponicParams(ph_target=6.0, ph_optimal=5.5)
    further_above = HydroponicParams(ph_target=6.5, ph_optimal=5.5)
    assert below.ph_availability_multiplier < at_optimum.ph_availability_multiplier
    assert above.ph_availability_multiplier < at_optimum.ph_availability_multiplier
    # No flat zone: 6.0 and 6.5 must differ, unlike the old [5.5, 6.5] plateau where they didn't.
    assert further_above.ph_availability_multiplier < above.ph_availability_multiplier


def test_ph_availability_multiplier_uses_its_own_higher_cap_than_a_single_nutrient():
    # A pH excursion large enough to hit its individual cap should lose more than any single
    # damped-tier nutrient's cap (ph_availability_penalty_cap_fraction=0.15 vs. 0.02 default).
    far_out = HydroponicParams(ph_target=10.0, ph_optimal=5.5)
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
