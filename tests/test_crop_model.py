from datetime import date

from twin.crop_model import (
    CropState,
    TomatoCropModel,
    _canopy_light_response,
    _lai,
    _temperature_response,
    _vpd_response,
)
from twin.params import CropParams


def _crop_params(**overrides) -> CropParams:
    defaults = dict(
        variety="Beefsteak tomato",
        planting_date=date(2026, 9, 15),
        density_plants_per_m2=2.5,
    )
    defaults.update(overrides)
    return CropParams(**defaults)


def test_more_light_increases_gross_assimilation():
    model = TomatoCropModel(_crop_params(), ground_area_m2=5000)
    state = CropState(days_after_planting=40.0, leaf_area_index=2.0, standing_dry_matter_g_m2=500.0)

    low_light = model.step(state, temp_in_c=22.0, co2_in_ppm=900.0, solar_rad_w_m2=100.0, dt_hours=1.0)
    high_light = model.step(state, temp_in_c=22.0, co2_in_ppm=900.0, solar_rad_w_m2=700.0, dt_hours=1.0)

    assert high_light.gross_assimilation_kg_co2_m2_hour > low_light.gross_assimilation_kg_co2_m2_hour


def test_higher_co2_increases_assimilation_up_to_saturation():
    model = TomatoCropModel(_crop_params(), ground_area_m2=5000)
    state = CropState(days_after_planting=40.0, leaf_area_index=2.0, standing_dry_matter_g_m2=500.0)

    low_co2 = model.step(state, temp_in_c=22.0, co2_in_ppm=420.0, solar_rad_w_m2=400.0, dt_hours=1.0)
    high_co2 = model.step(state, temp_in_c=22.0, co2_in_ppm=1000.0, solar_rad_w_m2=400.0, dt_hours=1.0)

    assert high_co2.gross_assimilation_kg_co2_m2_hour > low_co2.gross_assimilation_kg_co2_m2_hour


def test_no_assimilation_outside_temperature_range():
    model = TomatoCropModel(_crop_params(), ground_area_m2=5000)
    state = CropState(days_after_planting=40.0, leaf_area_index=2.0, standing_dry_matter_g_m2=500.0)

    freezing = model.step(state, temp_in_c=2.0, co2_in_ppm=900.0, solar_rad_w_m2=400.0, dt_hours=1.0)
    assert freezing.gross_assimilation_kg_co2_m2_hour == 0.0


def test_fruit_yield_only_accumulates_after_fruiting_start():
    model = TomatoCropModel(_crop_params(), ground_area_m2=5000)

    pre_fruiting = CropState(days_after_planting=10.0, leaf_area_index=1.0, standing_dry_matter_g_m2=100.0)
    result = model.step(pre_fruiting, temp_in_c=22.0, co2_in_ppm=900.0, solar_rad_w_m2=500.0, dt_hours=1.0)
    assert result.state.fruit_dry_matter_g_m2 == 0.0

    post_fruiting = CropState(days_after_planting=50.0, leaf_area_index=3.0, standing_dry_matter_g_m2=1000.0)
    result = model.step(post_fruiting, temp_in_c=22.0, co2_in_ppm=900.0, solar_rad_w_m2=500.0, dt_hours=1.0)
    assert result.state.fruit_dry_matter_g_m2 > 0.0


def test_lower_density_reduces_assimilation_below_reference():
    # reference_density_plants_per_m2 defaults to 2.5: below it, canopy
    # closes at a lower LAI and gross assimilation should drop accordingly.
    sparse = TomatoCropModel(_crop_params(density_plants_per_m2=1.0), ground_area_m2=5000)
    reference = TomatoCropModel(_crop_params(density_plants_per_m2=2.5), ground_area_m2=5000)
    state = CropState(days_after_planting=40.0, standing_dry_matter_g_m2=500.0)

    sparse_result = sparse.step(state, temp_in_c=22.0, co2_in_ppm=900.0, solar_rad_w_m2=500.0, dt_hours=1.0)
    reference_result = reference.step(state, temp_in_c=22.0, co2_in_ppm=900.0, solar_rad_w_m2=500.0, dt_hours=1.0)

    assert sparse_result.gross_assimilation_kg_co2_m2_hour < reference_result.gross_assimilation_kg_co2_m2_hour


def test_nighttime_respiration_reduces_standing_biomass():
    # No light (solar_rad=0) -> gross_assimilation=0 -> only respiration acts.
    # Regression check for a fixed bug where standing biomass was floored at its
    # previous value, silently discarding every hour of nighttime respiration.
    model = TomatoCropModel(_crop_params(), ground_area_m2=5000)
    state = CropState(days_after_planting=40.0, standing_dry_matter_g_m2=500.0)

    result = model.step(state, temp_in_c=18.0, co2_in_ppm=420.0, solar_rad_w_m2=0.0, dt_hours=1.0)

    assert result.state.standing_dry_matter_g_m2 < state.standing_dry_matter_g_m2


def test_density_above_reference_does_not_increase_assimilation():
    # Beyond canopy closure, extra plants add no more leaf area in this
    # simplified model — density is capped at reference_density_plants_per_m2.
    reference = TomatoCropModel(_crop_params(density_plants_per_m2=2.5), ground_area_m2=5000)
    dense = TomatoCropModel(_crop_params(density_plants_per_m2=4.0), ground_area_m2=5000)
    state = CropState(days_after_planting=40.0, standing_dry_matter_g_m2=500.0)

    reference_result = reference.step(state, temp_in_c=22.0, co2_in_ppm=900.0, solar_rad_w_m2=500.0, dt_hours=1.0)
    dense_result = dense.step(state, temp_in_c=22.0, co2_in_ppm=900.0, solar_rad_w_m2=500.0, dt_hours=1.0)

    assert dense_result.gross_assimilation_kg_co2_m2_hour == reference_result.gross_assimilation_kg_co2_m2_hour


def test_temperature_response_never_exceeds_one():
    # Regression check for a fixed bug: since T_OPT isn't equidistant from
    # T_MIN/T_MAX, the raw normalized product function could exceed 1.0
    # (peaked ~1.15 around 20-25C -- this greenhouse's normal operating range).
    for t in range(int(0), int(40)):
        assert _temperature_response(float(t)) <= 1.0


def test_vpd_response_never_exceeds_one_and_peaks_at_optimum():
    for v in [x / 10.0 for x in range(0, 30)]:
        assert _vpd_response(v) <= 1.0
    assert _vpd_response(0.85) == 1.0


def test_high_vpd_reduces_gross_assimilation():
    model = TomatoCropModel(_crop_params(), ground_area_m2=5000)
    state = CropState(days_after_planting=40.0, leaf_area_index=2.0, standing_dry_matter_g_m2=500.0)

    optimal_vpd = model.step(
        state, temp_in_c=22.0, co2_in_ppm=900.0, solar_rad_w_m2=500.0, dt_hours=1.0, vpd_kpa=0.85
    )
    stressful_vpd = model.step(
        state, temp_in_c=22.0, co2_in_ppm=900.0, solar_rad_w_m2=500.0, dt_hours=1.0, vpd_kpa=1.9
    )

    assert stressful_vpd.gross_assimilation_kg_co2_m2_hour < optimal_vpd.gross_assimilation_kg_co2_m2_hour


def test_co2_enrichment_boosts_lai_growth():
    # CO2 enrichment grows more/bigger leaves (not just faster instantaneous
    # photosynthesis) -- this is the season-long compounding channel behind
    # real CO2-enrichment yield gains that a single per-hour multiplier can't
    # represent on its own.
    params = _crop_params()
    ambient_lai = _lai(params, days_after_planting=40.0, co2_ppm=420.0)
    enriched_lai = _lai(params, days_after_planting=40.0, co2_ppm=700.0)

    assert enriched_lai > ambient_lai


def test_co2_lai_boost_caps_at_saturation_ppm():
    params = _crop_params()
    at_saturation = _lai(params, days_after_planting=40.0, co2_ppm=700.0)
    above_saturation = _lai(params, days_after_planting=40.0, co2_ppm=1200.0)

    assert at_saturation == above_saturation


def test_canopy_light_response_shows_diminishing_returns_with_lai():
    # Bug fix 2026-08-25: canopy assimilation used to be a flat single-leaf-rate * LAI
    # multiplication, implicitly assuming every leaf layer sees the same full incident
    # light. Real canopies self-shade -- doubling LAI should less than double the
    # canopy-integrated response, not scale it linearly.
    solar = 400.0
    single = _canopy_light_response(solar, lai=1.0)
    double = _canopy_light_response(solar, lai=2.0)

    assert single < double < 2 * single


def test_canopy_light_response_is_zero_with_no_light_or_no_leaves():
    assert _canopy_light_response(0.0, lai=3.0) == 0.0
    assert _canopy_light_response(500.0, lai=0.0) == 0.0


def test_canopy_assimilation_now_tracks_light_more_than_before_the_self_shading_fix():
    # The self-shading fix should widen (not narrow) the gap between low- and
    # high-light canopy assimilation, since a flat leaf-rate * LAI multiplication
    # over-credited low light disproportionately (self-shading barely matters when
    # incident light is already low -- the whole canopy is light-limited either way,
    # so the old flat approach overestimated low light assimilation more than it
    # overestimated high light assimilation).
    model = TomatoCropModel(_crop_params(), ground_area_m2=5000)
    state = CropState(days_after_planting=90.0, leaf_area_index=3.5, standing_dry_matter_g_m2=1500.0)

    low_light = model.step(state, temp_in_c=20.0, co2_in_ppm=700.0, solar_rad_w_m2=90.0, dt_hours=1.0)
    high_light = model.step(state, temp_in_c=20.0, co2_in_ppm=700.0, solar_rad_w_m2=270.0, dt_hours=1.0)

    # 3x the incident light should now yield noticeably more than 3x the naive
    # linear-in-light ratio the old flat model would have shown (~1.5x, matching
    # the flattened real-run seasonal sensitivity that motivated this fix).
    ratio = high_light.gross_assimilation_kg_co2_m2_hour / low_light.gross_assimilation_kg_co2_m2_hour
    assert ratio > 2.0
