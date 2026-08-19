"""Thin FastAPI layer over the twin/ simulation core.

The greenhouse configuration lives server-side (config/greenhouse_example.yaml
today, a real greenhouse's config later) — it is not something the frontend
edits per run. The frontend only triggers a simulation and reads results.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from twin.params import GreenhouseParams
from twin.simulate import run_simulation

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "greenhouse_example.yaml"

app = FastAPI(title="Greenhouse Digital Twin API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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


@app.post("/simulate")
def simulate() -> dict:
    params = GreenhouseParams.from_yaml(DEFAULT_CONFIG_PATH)
    results = run_simulation(params)

    daily = (
        results.set_index("timestamp")
        .resample("1D")
        .agg(
            {
                "temp_in_c": "mean",
                "temp_out_c": "mean",
                "co2_in_ppm": "mean",
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
