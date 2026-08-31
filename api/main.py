"""Thin FastAPI layer over the twin/ simulation core.

The greenhouse configuration lives server-side (config/greenhouse_example.yaml
today, a real greenhouse's config later) — it is not something the frontend
edits per run. The frontend only triggers a simulation and reads results.
"""

from __future__ import annotations

import copy
from datetime import date
from pathlib import Path

import yaml
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from twin.climate_model import CO2_DENSITY_KG_M3
from twin.params import GreenhouseParams
from twin.simulate import run_simulation
from twin.weather import load_weather

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "greenhouse_example.yaml"

app = FastAPI(title="Greenhouse Digital Twin API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    # Codespaces/Gitpod-style forwarded preview URLs (e.g. https://<name>-5173.app.github.dev)
    allow_origin_regex=r"https://.*\.app\.github\.dev",
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ValueError)
def _value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """twin/params.py raises plain ValueError on out-of-range overrides (e.g. a
    duration_days <= 0 or a dehumidification_setpoint_pct outside (0, 100]).
    Without this handler FastAPI lets it propagate as an unhandled 500 with a
    stack trace, instead of a client error the frontend can show to the user.
    """
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/config")
def get_config() -> dict:
    """The active backend config, for read-only display in the frontend."""
    with open(DEFAULT_CONFIG_PATH, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return _json_safe(raw)


@app.get("/weather_preview")
def weather_preview(start_date: date | None = None, duration_days: int | None = None) -> dict:
    """Daily-mean outdoor temperature/solar radiation for the weather tab, so the
    user can see what the selected source/period looks like before spending time
    on a full climate+crop run. Just the weather loader (twin/weather.py) --
    no climate model, no crop model, effectively free to compute.
    """
    with open(DEFAULT_CONFIG_PATH, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    params = GreenhouseParams.from_dict(raw)
    effective_start = start_date if start_date is not None else params.simulation.start_date
    effective_duration = duration_days if duration_days is not None else params.simulation.duration_days
    df = load_weather(params.weather, effective_start, effective_duration, params.simulation.timestep_hours)
    daily = (
        df.set_index("timestamp")
        .resample("1D")
        .agg({"temp_out_c": "mean", "solar_rad_w_m2": "mean"})
        .reset_index()
    )
    return {
        "daily_series": [
            {
                "date": row.timestamp.date().isoformat(),
                "temp_out_c": round(row.temp_out_c, 2),
                "solar_rad_w_m2": round(row.solar_rad_w_m2, 1),
            }
            for row in daily.itertuples()
        ]
    }


class SimulateRequest(BaseModel):
    """Run-level overrides a user can pick per simulation.

    Structural greenhouse parameters (area, CHP size, geometry) are not
    here on purpose — they stay in the backend config, see module docstring.
    All fields optional; anything omitted falls back to the config default.
    """

    start_date: date | None = None
    duration_days: int | None = None
    crop_variety: str | None = None
    crop_density_plants_per_m2: float | None = None
    heating_setpoint_day_c: float | None = None
    heating_setpoint_night_c: float | None = None
    co2_setpoint_day_ppm: float | None = None
    dehumidification_setpoint_pct: float | None = None
    # Hydroponics recipe (see docs/assumptions/hydroponics.md "Level B" + damped recipe tier) --
    # the only recipe fields with a real modeled effect, so the only ones exposed as overrides.
    # The informational tier (P/S/Fe/Mn/Zn/Cu/Mo) has no model effect, so isn't here.
    ec_target_ms_cm: float | None = None
    ph_target: float | None = None
    n_ppm: float | None = None
    k_ppm: float | None = None
    mg_ppm: float | None = None
    b_ppm: float | None = None


def _apply_overrides(raw: dict, overrides: SimulateRequest) -> dict:
    raw = copy.deepcopy(raw)
    if overrides.start_date is not None:
        raw["simulation"]["start_date"] = overrides.start_date
    if overrides.duration_days is not None:
        raw["simulation"]["duration_days"] = overrides.duration_days
    if overrides.crop_variety is not None:
        raw["crop"]["variety"] = overrides.crop_variety
    if overrides.crop_density_plants_per_m2 is not None:
        raw["crop"]["density_plants_per_m2"] = overrides.crop_density_plants_per_m2
    climate = raw.setdefault("climate_control", {})
    if overrides.heating_setpoint_day_c is not None:
        climate["heating_setpoint_day_c"] = overrides.heating_setpoint_day_c
    if overrides.heating_setpoint_night_c is not None:
        climate["heating_setpoint_night_c"] = overrides.heating_setpoint_night_c
    if overrides.co2_setpoint_day_ppm is not None:
        climate["co2_setpoint_day_ppm"] = overrides.co2_setpoint_day_ppm
    if overrides.dehumidification_setpoint_pct is not None:
        climate["dehumidification_setpoint_pct"] = overrides.dehumidification_setpoint_pct
    hydro = raw.setdefault("hydroponic", {})
    if overrides.ec_target_ms_cm is not None:
        hydro["ec_target_ms_cm"] = overrides.ec_target_ms_cm
    if overrides.ph_target is not None:
        hydro["ph_target"] = overrides.ph_target
    if overrides.n_ppm is not None:
        hydro["n_ppm"] = overrides.n_ppm
    if overrides.k_ppm is not None:
        hydro["k_ppm"] = overrides.k_ppm
    if overrides.mg_ppm is not None:
        hydro["mg_ppm"] = overrides.mg_ppm
    if overrides.b_ppm is not None:
        hydro["b_ppm"] = overrides.b_ppm
    return raw


@app.post("/simulate")
def simulate(overrides: SimulateRequest = SimulateRequest()) -> dict:
    with open(DEFAULT_CONFIG_PATH, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    raw = _apply_overrides(raw, overrides)
    params = GreenhouseParams.from_dict(raw)
    results = run_simulation(params)

    # CO2 dosing only targets co2_setpoint_day_ppm during the day -- at night the target is
    # co2_ambient_ppm on purpose (no point enriching CO2 when there's no light for
    # photosynthesis to use it), so a plain 24h mean always sits well below the day setpoint
    # even when dosing hits it exactly every daytime hour. Daytime-only mean is what's
    # actually meaningful to chart against the day setpoint.
    daytime_mask = results["timestamp"].dt.hour.between(
        params.climate_control.day_start_hour, params.climate_control.day_end_hour - 1
    )
    daytime_co2_by_day = (
        results.loc[daytime_mask].assign(date=lambda d: d["timestamp"].dt.date).groupby("date")["co2_in_ppm"].mean()
    )

    daily = (
        results.set_index("timestamp")
        .resample("1D")
        .agg(
            {
                "temp_in_c": "mean",
                "temp_out_c": "mean",
                "rh_in_pct": "mean",
                "vpd_kpa": "mean",
                "fruit_fresh_yield_kg_m2": "last",
                # Daily-average power draw (kW), i.e. normalized per hour — not a daily total —
                # so it's directly comparable to the CHP's fixed max heat output below.
                "heat_used_kw": "mean",
                "screen_deployed": "sum",  # hours deployed that day (timestep is hourly)
                "fan_pad_active": "sum",  # hours engaged that day (timestep is hourly)
                # Daily-average power draw (kW) -- same normalization as heat_used_kw above.
                "dehumidification_elec_kw": "mean",
                "ventilation_elec_kw": "mean",
                "recirculation_elec_kw": "mean",
                "fertigation_elec_kw": "mean",
                "fruit_set_fraction": "mean",
                # Volumes/masses (unlike the kW rates above) are daily totals, not hourly
                # averages -- a grower thinks in liters/kg dosed per day, not an average rate.
                "irrigation_water_kg_per_hour": "sum",
                "drainage_water_kg_per_hour": "sum",
                "fertilizer_dosed_g_per_hour": "sum",
            }
        )
        .reset_index()
        .rename(
            columns={
                "screen_deployed": "screen_closed_hours",
                "fan_pad_active": "fan_pad_active_hours",
                "irrigation_water_kg_per_hour": "irrigation_water_l_day",
                "drainage_water_kg_per_hour": "drainage_water_l_day",
                "fertilizer_dosed_g_per_hour": "fertilizer_dosed_g_day",
            }
        )
    )
    daily["screen_closed_hours"] = daily["screen_closed_hours"] * params.simulation.timestep_hours
    daily["fan_pad_active_hours"] = daily["fan_pad_active_hours"] * params.simulation.timestep_hours
    # Same "sum an hourly rate, then scale by timestep_hours" pattern as the hours-fields above --
    # correct even if timestep_hours isn't exactly 1.
    daily["irrigation_water_l_day"] = daily["irrigation_water_l_day"] * params.simulation.timestep_hours
    daily["drainage_water_l_day"] = daily["drainage_water_l_day"] * params.simulation.timestep_hours
    daily["fertilizer_dosed_g_day"] = daily["fertilizer_dosed_g_day"] * params.simulation.timestep_hours
    daily["co2_in_ppm"] = daily["timestamp"].dt.date.map(daytime_co2_by_day)
    daily["fruit_set_pct"] = daily["fruit_set_fraction"] * 100.0

    final_yield_kg_m2 = float(results["fruit_fresh_yield_kg_m2"].iloc[-1])
    avg_fruit_set_pct = float(results["fruit_set_fraction"].mean() * 100.0)
    # Trusses/week: not a directly-modeled quantity -- derived by converting the model's
    # cumulative fruit yield into truss-equivalents via the variety's target fruit weight and
    # fruits-per-truss (twin/params.py CropParams), then averaged over the whole run. Divides
    # by *stem* density (density_plants_per_m2 * stems_per_plant), not plant density -- each
    # stem carries its own trusses, so a two-stem plant's yield is shared across two stems'
    # worth of truss production, matching how a real grower actually reports "trusses/week"
    # (per stem, not per plant). A real grower counts trusses directly; this model tracks
    # continuous dry-matter partitioning instead, so this is a reporting conversion, not new
    # crop-model physics.
    stem_density_per_m2 = params.crop.density_plants_per_m2 * params.crop.stems_per_plant
    final_trusses_per_stem = (
        final_yield_kg_m2 * 1000.0 / stem_density_per_m2 / (params.crop.target_fruit_weight_g * params.crop.fruits_per_truss)
    )
    avg_truss_rate_per_week = final_trusses_per_stem / (params.simulation.duration_days / 7.0)
    # The whole-season average above is diluted by the ~55-day vegetative/ramp-up window
    # (near-zero production before fruiting even starts) and by any partial final week -- neither
    # is what a grower means by "trusses/week" (that's the steady, full-production-phase pace).
    # Recompute the same conversion using only the yield accumulated after the ramp finishes.
    full_production_start_day = int(params.crop.fruiting_start_days + params.crop.fruiting_ramp_days)
    steady_state_truss_rate_per_week = None
    if params.simulation.duration_days > full_production_start_day:
        yield_at_full_production_start_kg_m2 = float(
            daily["fruit_fresh_yield_kg_m2"].iloc[full_production_start_day - 1]
        )
        steady_state_days = params.simulation.duration_days - full_production_start_day
        steady_state_trusses_per_stem = (
            (final_yield_kg_m2 - yield_at_full_production_start_kg_m2)
            * 1000.0
            / stem_density_per_m2
            / (params.crop.target_fruit_weight_g * params.crop.fruits_per_truss)
        )
        steady_state_truss_rate_per_week = steady_state_trusses_per_stem / (steady_state_days / 7.0)
    # heat_used_kw is an hourly instantaneous rate; sum(kW readings) * timestep_hours gives the
    # season's total energy (kWh). It is already hard-capped at the CHP's fixed heat output
    # every hour (twin/climate_model.py: heat_used_w = min(required_w, heat_available_w)), so it
    # can never exceed max_heat_available_kw * duration_hours.
    total_heat_used_kwh = float(results["heat_used_kw"].sum() * params.simulation.timestep_hours)
    heat_loss_avoided_kwh = float(results["heat_loss_avoided_kw"].sum() * params.simulation.timestep_hours)
    screen_deployed_pct = float(results["screen_deployed"].mean() * 100.0)
    fan_pad_active_pct = float(results["fan_pad_active"].mean() * 100.0)
    # Grid-purchased electricity for the greenhouse's own consumption -- the CHP's electricity is
    # sold to the grid, not netted against this (see docs/assumptions/economics.md).
    total_dehumidification_elec_kwh = float(results["dehumidification_elec_kw"].sum() * params.simulation.timestep_hours)
    total_ventilation_elec_kwh = float(results["ventilation_elec_kw"].sum() * params.simulation.timestep_hours)
    total_recirculation_elec_kwh = float(results["recirculation_elec_kw"].sum() * params.simulation.timestep_hours)
    total_fertigation_elec_kwh = float(results["fertigation_elec_kw"].sum() * params.simulation.timestep_hours)
    total_electricity_kwh = (
        total_dehumidification_elec_kwh
        + total_ventilation_elec_kwh
        + total_recirculation_elec_kwh
        + total_fertigation_elec_kwh
    )
    # Hydroponic Level A (see docs/assumptions/hydroponics.md): water/fertilizer totals, derived
    # from the crop's own transpiration -- not new crop-model physics.
    total_irrigation_water_m3 = float(results["irrigation_water_kg_per_hour"].sum() * params.simulation.timestep_hours / 1000.0)
    total_drainage_water_m3 = float(results["drainage_water_kg_per_hour"].sum() * params.simulation.timestep_hours / 1000.0)
    total_fertilizer_dosed_kg = float(results["fertilizer_dosed_g_per_hour"].sum() * params.simulation.timestep_hours / 1000.0)
    # Theoretical ceiling: the ppm the CHP's full hourly CO2 output would add on top of
    # ambient if every bit of it stayed in the greenhouse air for that hour (zero
    # ventilation loss) -- an upper bound on what "the machine can offer", not a realistic
    # steady-state level (real dosing also has to fight ventilation exchange).
    max_co2_available_ppm = params.climate_control.co2_ambient_ppm + (
        params.chp.co2_available_kg_per_hour / CO2_DENSITY_KG_M3 / params.geometry.volume_m3 * 1e6
    )
    # Hydroponic Level B (see docs/assumptions/hydroponics.md "Level B"): EC -> fruit dry-matter
    # (B1), the real bell-shaped EC/yield response (BER risk above the high threshold, nutrient
    # deficiency below the low threshold), pH -> nutrient-availability yield loss, plus the
    # damped N/K/Mg/B recipe tier. All applied as post-hoc scalar adjustments to
    # final_yield_kg_m2, not inside the crop model's hourly loop (EC/pH/recipe are static config
    # values for the whole run in this design).
    # NAMING CAVEAT (flagged by the user 2026-08-29, not yet resolved): "marketable" strictly
    # means output that passes quality control and can be sold. Of the four factors combined
    # below, only ber_yield_loss_fraction is actually that (BER is a real fruit defect that gets
    # a fruit rejected) -- the other three (B1 dry-matter, ph_availability_multiplier,
    # recipe_adequacy_multiplier) are changes to the plant's *total biological* yield (it grows
    # less), not produce that grew normally and then got culled. Left as one combined
    # "marketable_yield_kg_m2" number for now (explicit user decision) -- revisit before treating
    # this as an economically meaningful "sellable" figure. See docs/assumptions/hydroponics.md.
    hydro = params.hydroponic
    ec_adjusted_final_yield_kg_m2 = final_yield_kg_m2 / hydro.effective_dry_matter_content_fruit
    ber_yield_loss_fraction = hydro.ber_yield_loss_fraction
    ec_deficiency_yield_loss_fraction = hydro.ec_deficiency_yield_loss_fraction
    ph_availability_multiplier = hydro.ph_availability_multiplier
    recipe_adequacy_multiplier = hydro.recipe_adequacy_multiplier
    marketable_yield_kg_m2 = (
        ec_adjusted_final_yield_kg_m2
        * (1.0 - ber_yield_loss_fraction)
        * (1.0 - ec_deficiency_yield_loss_fraction)
        * ph_availability_multiplier
        * recipe_adequacy_multiplier
    )
    total_marketable_yield_kg = marketable_yield_kg_m2 * params.geometry.area_m2
    # B1/B2/B2b/pH/recipe are all constant multiplicative factors for the whole run (EC/pH/recipe
    # are static config values, not time-varying), so the same ratio applies at any day, not just
    # the final one -- lets daily_series carry a marketable curve consistent with the summary's
    # marketable_yield_kg_m2, instead of every other yield display in the app going stale/frozen
    # relative to it whenever EC/pH/recipe move away from their reference values.
    marketable_yield_ratio = marketable_yield_kg_m2 / final_yield_kg_m2 if final_yield_kg_m2 > 0 else 1.0

    return {
        "greenhouse_name": params.name,
        "summary": {
            "final_yield_kg_m2": final_yield_kg_m2,
            "total_yield_kg": final_yield_kg_m2 * params.geometry.area_m2,
            "ec_adjusted_final_yield_kg_m2": ec_adjusted_final_yield_kg_m2,
            "ber_yield_loss_fraction": ber_yield_loss_fraction,
            "ec_deficiency_yield_loss_fraction": ec_deficiency_yield_loss_fraction,
            "ph_availability_multiplier": ph_availability_multiplier,
            "recipe_adequacy_multiplier": recipe_adequacy_multiplier,
            "marketable_yield_kg_m2": marketable_yield_kg_m2,
            "total_marketable_yield_kg": total_marketable_yield_kg,
            "area_m2": params.geometry.area_m2,
            "duration_days": params.simulation.duration_days,
            "total_heat_used_kwh": total_heat_used_kwh,
            "max_heat_available_kw": params.chp.heat_available_kw,
            "heat_loss_avoided_kwh": heat_loss_avoided_kwh,
            "screen_deployed_pct": screen_deployed_pct,
            "fan_pad_active_pct": fan_pad_active_pct,
            "total_dehumidification_elec_kwh": total_dehumidification_elec_kwh,
            "total_ventilation_elec_kwh": total_ventilation_elec_kwh,
            "total_recirculation_elec_kwh": total_recirculation_elec_kwh,
            "total_fertigation_elec_kwh": total_fertigation_elec_kwh,
            "total_electricity_kwh": total_electricity_kwh,
            "total_irrigation_water_m3": total_irrigation_water_m3,
            "total_drainage_water_m3": total_drainage_water_m3,
            "total_fertilizer_dosed_kg": total_fertilizer_dosed_kg,
            "avg_fruit_set_pct": avg_fruit_set_pct,
            "final_trusses_per_stem": final_trusses_per_stem,
            "avg_truss_rate_per_week": avg_truss_rate_per_week,
            "full_production_start_day": full_production_start_day,
            "steady_state_truss_rate_per_week": steady_state_truss_rate_per_week,
            "co2_ambient_ppm": params.climate_control.co2_ambient_ppm,
            "max_co2_available_ppm": max_co2_available_ppm,
        },
        "daily_series": [
            {
                "date": row.timestamp.date().isoformat(),
                "temp_in_c": round(row.temp_in_c, 2),
                "temp_out_c": round(row.temp_out_c, 2),
                "co2_in_ppm": round(row.co2_in_ppm, 1),
                "rh_in_pct": round(row.rh_in_pct, 1),
                "vpd_kpa": round(row.vpd_kpa, 3),
                "fruit_fresh_yield_kg_m2": round(row.fruit_fresh_yield_kg_m2, 3),
                "marketable_yield_kg_m2": round(row.fruit_fresh_yield_kg_m2 * marketable_yield_ratio, 3),
                "heat_used_kw": round(row.heat_used_kw, 1),
                "screen_closed_hours": round(row.screen_closed_hours, 1),
                "fan_pad_active_hours": round(row.fan_pad_active_hours, 1),
                "dehumidification_elec_kw": round(row.dehumidification_elec_kw, 2),
                "ventilation_elec_kw": round(row.ventilation_elec_kw, 2),
                "recirculation_elec_kw": round(row.recirculation_elec_kw, 2),
                "fertigation_elec_kw": round(row.fertigation_elec_kw, 2),
                "irrigation_water_l_day": round(row.irrigation_water_l_day, 1),
                "drainage_water_l_day": round(row.drainage_water_l_day, 1),
                "fertilizer_dosed_g_day": round(row.fertilizer_dosed_g_day, 1),
                "fruit_set_pct": round(row.fruit_set_pct, 1),
            }
            for row in daily.itertuples()
        ],
    }


def _json_safe(value):
    """Recursively convert YAML-loaded values (e.g. datetime.date) to JSON-safe types."""
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
