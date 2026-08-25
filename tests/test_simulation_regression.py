"""End-to-end regression test for the full simulation pipeline.

Unlike test_climate_model.py / test_crop_model.py (which test each model's
physics in isolation with synthetic inputs), this runs the real example
config end-to-end -- the same path run_simulation.py exercises -- and
asserts the season-level results stay within a plausible range. It exists to
catch a regression in how the climate and crop models interact through
twin/simulate.py that per-model unit tests, by construction, can't see.

The bounds are intentionally loose: this is a smoke/regression test, not a
calibration check. A legitimate model change (a bug fix, a recalibration)
may need these bounds nudged -- that's expected and fine. What it should
catch is an accidental regression that silently zeroes out yield, blows up
temperature, or otherwise breaks the climate<->crop feedback loop.
"""

from __future__ import annotations

from pathlib import Path

from twin.params import GreenhouseParams
from twin.simulate import run_simulation

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "greenhouse_example.yaml"


def _run():
    params = GreenhouseParams.from_yaml(CONFIG_PATH)
    return params, run_simulation(params)


def test_full_season_yield_is_in_a_plausible_range():
    _, results = _run()
    final_yield_kg_m2 = results["fruit_fresh_yield_kg_m2"].iloc[-1]
    assert 3.0 < final_yield_kg_m2 < 12.0


def test_full_season_yield_is_monotonically_non_decreasing():
    _, results = _run()
    yield_series = results["fruit_fresh_yield_kg_m2"]
    assert (yield_series.diff().dropna() >= 0).all()


def test_full_season_indoor_temperature_stays_within_a_sane_band():
    _, results = _run()
    # Loose band: the CHP can't perfectly track setpoints under every weather
    # draw, but indoor air should never run away far outside them.
    assert results["temp_in_c"].min() > 5.0
    assert results["temp_in_c"].max() < 40.0


def test_full_season_produces_one_row_per_simulated_hour():
    params, results = _run()
    expected_rows = int(params.simulation.duration_days * 24 / params.simulation.timestep_hours)
    assert len(results) == expected_rows


def test_full_season_heat_used_never_exceeds_chp_capacity():
    params, results = _run()
    assert results["heat_used_kw"].max() <= params.chp.heat_available_kw + 1e-6
