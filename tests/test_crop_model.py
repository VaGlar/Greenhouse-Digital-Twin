from datetime import date

from twin.crop_model import CropState, TomatoCropModel
from twin.params import CropParams


def _crop_params() -> CropParams:
    return CropParams(
        variety="Beefsteak tomato",
        planting_date=date(2026, 9, 15),
        density_plants_per_m2=2.5,
    )


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
