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
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from twin.params import GreenhouseParams
from twin.simulate import run_simulation

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


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/config")
def get_config() -> dict:
    """The active backend config, for read-only display in the frontend."""
    with open(DEFAULT_CONFIG_PATH, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return _json_safe(raw)


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
    return raw


@app.post("/simulate")
def simulate(overrides: SimulateRequest = SimulateRequest()) -> dict:
    with open(DEFAULT_CONFIG_PATH, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    raw = _apply_overrides(raw, overrides)
    params = GreenhouseParams.from_dict(raw)
    results = run_simulation(params)

    daily = (
        results.set_index("timestamp")
        .resample("1D")
        .agg(
            {
                "temp_in_c": "mean",
                "temp_out_c": "mean",
                "co2_in_ppm": "mean",
                "rh_in_pct": "mean",
                "vpd_kpa": "mean",
                "fruit_fresh_yield_kg_m2": "last",
            }
        )
        .reset_index()
    )

    final_yield_kg_m2 = float(results["fruit_fresh_yield_kg_m2"].iloc[-1])

    return {
        "greenhouse_name": params.name,
        "summary": {
            "final_yield_kg_m2": final_yield_kg_m2,
            "total_yield_kg": final_yield_kg_m2 * params.geometry.area_m2,
            "area_m2": params.geometry.area_m2,
            "duration_days": params.simulation.duration_days,
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
