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

        crop_result = crop_model.step(
            crop_state,
            temp_in_c=climate_state.temp_in_c,
            co2_in_ppm=climate_state.co2_in_ppm,
            solar_rad_w_m2=row["solar_rad_w_m2"],
            dt_hours=dt_hours,
        )
        co2_uptake_kg_per_hour = crop_result.gross_assimilation_kg_co2_m2_hour * params.geometry.area_m2

        climate_result = climate_model.step(
            climate_state,
            hour=hour,
            temp_out_c=row["temp_out_c"],
            solar_rad_w_m2=row["solar_rad_w_m2"],
            dt_hours=dt_hours,
            co2_uptake_kg_per_hour=co2_uptake_kg_per_hour,
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
                "vent_ach": climate_result.vent_ach,
                "co2_injected_kg": climate_result.co2_injected_kg,
                "co2_dumped_kg": climate_result.co2_dumped_kg,
                "days_after_planting": crop_state.days_after_planting,
                "leaf_area_index": crop_state.leaf_area_index,
                "standing_dry_matter_g_m2": crop_state.standing_dry_matter_g_m2,
                "fruit_fresh_yield_kg_m2": crop_state.fruit_fresh_yield_kg_m2,
            }
        )

    return pd.DataFrame(records)
