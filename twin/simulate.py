"""Orchestrates the hour-by-hour climate + crop simulation loop."""

from __future__ import annotations

import pandas as pd

from twin.climate_model import ClimateState, GreenhouseClimateModel
from twin.crop_model import CropState, TomatoCropModel
from twin.params import GreenhouseParams
from twin.weather import load_weather


def run_simulation(params: GreenhouseParams) -> pd.DataFrame:
    weather_df = load_weather(
        params.weather,
        start_date=params.simulation.start_date,
        duration_days=params.simulation.duration_days,
        timestep_hours=params.simulation.timestep_hours,
    )

    climate_model = GreenhouseClimateModel(params.geometry, params.chp, params.climate_control)
    crop_model = TomatoCropModel(params.crop, params.geometry.area_m2)

    climate_state = ClimateState(
        temp_in_c=params.climate_control.heating_setpoint_night_c,
        co2_in_ppm=params.climate_control.co2_ambient_ppm,
    )
    crop_state = CropState()

    dt_hours = params.simulation.timestep_hours
    records = []

    for _, row in weather_df.iterrows():
        hour = row["timestamp"].hour

        # Decided once per hour and fed to both models, so the crop's shaded light and the
        # climate model's energy balance always agree on whether the screen is deployed.
        screen_deployed = climate_model.decide_screen_deployment(
            climate_state,
            hour=hour,
            temp_out_c=row["temp_out_c"],
            solar_rad_w_m2=row["solar_rad_w_m2"],
            dt_hours=dt_hours,
            rh_out_pct=row["rh_out_pct"],
        )
        shaded_solar_rad_w_m2 = row["solar_rad_w_m2"] * (
            1.0 - params.climate_control.screen_energy_saving_fraction if screen_deployed else 1.0
        )

        crop_result = crop_model.step(
            crop_state,
            temp_in_c=climate_state.temp_in_c,
            co2_in_ppm=climate_state.co2_in_ppm,
            solar_rad_w_m2=shaded_solar_rad_w_m2,
            dt_hours=dt_hours,
            vpd_kpa=climate_state.vpd_kpa,
        )
        co2_uptake_kg_per_hour = crop_result.gross_assimilation_kg_co2_m2_hour * params.geometry.area_m2
        transpiration_kg_per_hour = crop_result.transpiration_kg_m2_hour * params.geometry.area_m2

        climate_result = climate_model.step(
            climate_state,
            hour=hour,
            temp_out_c=row["temp_out_c"],
            solar_rad_w_m2=row["solar_rad_w_m2"],
            dt_hours=dt_hours,
            co2_uptake_kg_per_hour=co2_uptake_kg_per_hour,
            rh_out_pct=row["rh_out_pct"],
            transpiration_kg_per_hour=transpiration_kg_per_hour,
            screen_deployed=screen_deployed,
        )

        climate_state = climate_result.state
        crop_state = crop_result.state

        records.append(
            {
                "timestamp": row["timestamp"],
                "temp_out_c": row["temp_out_c"],
                "solar_rad_w_m2": row["solar_rad_w_m2"],
                "temp_in_c": climate_state.temp_in_c,
                "co2_in_ppm": climate_state.co2_in_ppm,
                "heat_used_kw": climate_result.heat_used_kw,
                "heat_dumped_kw": climate_result.heat_dumped_kw,
                "screen_deployed": climate_result.screen_deployed,
                "heat_loss_avoided_kw": climate_result.heat_loss_avoided_kw,
                "vent_ach": climate_result.vent_ach,
                "co2_injected_kg": climate_result.co2_injected_kg,
                "co2_dumped_kg": climate_result.co2_dumped_kg,
                "rh_in_pct": climate_result.rh_in_pct,
                "vpd_kpa": climate_result.vpd_kpa,
                "condensed_kg": climate_result.condensed_kg,
                "dehumidified_kg": climate_result.dehumidified_kg,
                "days_after_planting": crop_state.days_after_planting,
                "leaf_area_index": crop_state.leaf_area_index,
                "standing_dry_matter_g_m2": crop_state.standing_dry_matter_g_m2,
                "fruit_fresh_yield_kg_m2": crop_state.fruit_fresh_yield_kg_m2,
            }
        )

    return pd.DataFrame(records)
