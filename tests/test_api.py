"""Tests for the FastAPI layer (api/main.py).

Uses small duration_days overrides everywhere a simulation actually needs to
run, so the suite stays fast -- the physics itself is covered by
test_climate_model.py / test_crop_model.py / test_weather.py, not here.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_config_returns_the_backend_config():
    response = client.get("/config")
    assert response.status_code == 200
    body = response.json()
    assert "name" in body
    assert "geometry" in body
    assert "chp" in body
    # dates must have been converted to plain strings, not left as python objects
    assert isinstance(body["simulation"]["start_date"], str)


def test_simulate_with_no_overrides_uses_backend_config_defaults():
    response = client.post("/simulate", json={})
    assert response.status_code == 200
    body = response.json()
    assert "greenhouse_name" in body
    assert "summary" in body
    assert "daily_series" in body
    assert len(body["daily_series"]) == body["summary"]["duration_days"]


def test_simulate_duration_override_shortens_the_run():
    response = client.post("/simulate", json={"duration_days": 3})
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["duration_days"] == 3
    assert len(body["daily_series"]) == 3


def test_simulate_response_has_expected_summary_fields():
    response = client.post("/simulate", json={"duration_days": 2})
    assert response.status_code == 200
    summary = response.json()["summary"]
    for key in (
        "final_yield_kg_m2",
        "total_yield_kg",
        "area_m2",
        "duration_days",
        "total_heat_used_kwh",
        "max_heat_available_kw",
        "heat_loss_avoided_kwh",
        "screen_deployed_pct",
        "fan_pad_active_pct",
        "total_dehumidification_elec_kwh",
        "total_ventilation_elec_kwh",
        "total_recirculation_elec_kwh",
        "total_fertigation_elec_kwh",
        "total_electricity_kwh",
        "total_irrigation_water_m3",
        "total_drainage_water_m3",
        "total_fertilizer_dosed_kg",
        "avg_fruit_set_pct",
        "final_trusses_per_stem",
        "avg_truss_rate_per_week",
        "full_production_start_day",
        "steady_state_truss_rate_per_week",
        "co2_ambient_ppm",
        "max_co2_available_ppm",
        "ec_adjusted_final_yield_kg_m2",
        "ber_yield_loss_fraction",
        "recipe_adequacy_multiplier",
        "marketable_yield_kg_m2",
        "total_marketable_yield_kg",
    ):
        assert key in summary


def test_simulate_daily_series_rows_have_expected_fields():
    response = client.post("/simulate", json={"duration_days": 2})
    assert response.status_code == 200
    row = response.json()["daily_series"][0]
    for key in (
        "date",
        "temp_in_c",
        "temp_out_c",
        "co2_in_ppm",
        "rh_in_pct",
        "vpd_kpa",
        "fruit_fresh_yield_kg_m2",
        "heat_used_kw",
        "screen_closed_hours",
        "fan_pad_active_hours",
        "dehumidification_elec_kw",
        "ventilation_elec_kw",
        "recirculation_elec_kw",
        "fertigation_elec_kw",
        "irrigation_water_l_day",
        "drainage_water_l_day",
        "fertilizer_dosed_g_day",
        "fruit_set_pct",
    ):
        assert key in row


def test_simulate_heating_setpoint_override_changes_indoor_temperature():
    cold = client.post(
        "/simulate", json={"duration_days": 3, "heating_setpoint_day_c": 15, "heating_setpoint_night_c": 12}
    ).json()
    warm = client.post(
        "/simulate", json={"duration_days": 3, "heating_setpoint_day_c": 25, "heating_setpoint_night_c": 22}
    ).json()
    cold_mean_temp = sum(r["temp_in_c"] for r in cold["daily_series"]) / len(cold["daily_series"])
    warm_mean_temp = sum(r["temp_in_c"] for r in warm["daily_series"]) / len(warm["daily_series"])
    assert warm_mean_temp > cold_mean_temp


# -- invalid overrides: twin/params.py validation must surface as a 422, not a 500 --


def test_simulate_rejects_zero_duration_days():
    response = client.post("/simulate", json={"duration_days": 0})
    assert response.status_code == 422
    assert "duration_days" in response.json()["detail"]


def test_simulate_rejects_negative_duration_days():
    response = client.post("/simulate", json={"duration_days": -5})
    assert response.status_code == 422


def test_simulate_rejects_negative_crop_density():
    response = client.post("/simulate", json={"crop_density_plants_per_m2": -1})
    assert response.status_code == 422
    assert "density_plants_per_m2" in response.json()["detail"]


def test_simulate_rejects_dehumidification_setpoint_at_zero():
    response = client.post("/simulate", json={"dehumidification_setpoint_pct": 0})
    assert response.status_code == 422


def test_simulate_rejects_dehumidification_setpoint_above_100():
    response = client.post("/simulate", json={"dehumidification_setpoint_pct": 150})
    assert response.status_code == 422


# -- malformed request bodies: pydantic should reject these before they reach twin/params.py --


def test_simulate_rejects_non_integer_duration_days():
    response = client.post("/simulate", json={"duration_days": "abc"})
    assert response.status_code == 422


def test_simulate_rejects_malformed_start_date():
    response = client.post("/simulate", json={"start_date": "not-a-date"})
    assert response.status_code == 422


# -- electricity consumption summary fields --


def test_total_electricity_kwh_is_sum_of_its_components():
    body = client.post("/simulate", json={"duration_days": 5}).json()
    summary = body["summary"]
    assert summary["total_electricity_kwh"] == pytest.approx(
        summary["total_dehumidification_elec_kwh"]
        + summary["total_ventilation_elec_kwh"]
        + summary["total_recirculation_elec_kwh"]
        + summary["total_fertigation_elec_kwh"]
    )


# -- hydroponics (Level A: fertigation water/electricity, derived from transpiration) --


def test_drainage_water_is_irrigation_minus_transpiration_and_matches_drainage_fraction():
    body = client.post("/simulate", json={"duration_days": 10}).json()
    summary = body["summary"]
    config = client.get("/config").json()
    drainage_fraction = config["hydroponic"]["drainage_target_fraction"]

    assert summary["total_drainage_water_m3"] > 0
    # drainage = irrigation * drainage_fraction, by construction (irrigation = transpiration /
    # (1 - fraction), so drainage = irrigation - transpiration = irrigation * fraction).
    assert summary["total_drainage_water_m3"] == pytest.approx(
        summary["total_irrigation_water_m3"] * drainage_fraction, rel=1e-6
    )
    assert summary["total_irrigation_water_m3"] > summary["total_drainage_water_m3"]


def test_fertilizer_dosed_is_consistent_with_irrigation_volume_and_ec_target():
    summary = client.post("/simulate", json={"duration_days": 10}).json()["summary"]
    # SimulationOverrides has no ec_target field yet -- Level A only exposes it via config, not
    # as a request override -- so cross-check the derivation formula against config defaults.
    config = client.get("/config").json()
    ec = config["hydroponic"]["ec_target_ms_cm"]
    fertilizer_g_per_l_per_ec = config["hydroponic"]["fertilizer_g_per_l_per_ec_unit"]
    expected_fertilizer_kg = summary["total_irrigation_water_m3"] * 1000.0 * ec * fertilizer_g_per_l_per_ec / 1000.0
    assert summary["total_fertilizer_dosed_kg"] == pytest.approx(expected_fertilizer_kg, rel=1e-6)


def test_fertigation_electricity_is_zero_when_transpiration_is_zero():
    # duration_days=1 starting at night-heavy winter date still has some daylight hours with
    # transpiration, so instead directly verify the zero-transpiration-hour behavior via the
    # daily series: any day with irrigation_water_l_day == 0 must also have fertigation_elec_kw
    # averaging to 0 and no fertilizer dosed.
    body = client.post("/simulate", json={"duration_days": 5}).json()
    for row in body["daily_series"]:
        if row["irrigation_water_l_day"] == 0:
            assert row["fertigation_elec_kw"] == 0
            assert row["fertilizer_dosed_g_day"] == 0


# -- hydroponics Level B (EC -> fruit dry matter / BER risk, damped N/K/Mg/B recipe tier) --


def test_marketable_yield_equals_default_config_at_default_ec():
    # Default config: ec_target_ms_cm=3.0 (below the 3.5 BER threshold) and n/k/mg/b_ppm all
    # inside their sufficiency ranges -- so B2 and the recipe tier contribute nothing, only B1's
    # small EC-vs-2.3-reference dry-matter adjustment applies. duration_days must be past
    # fruiting_start_days (config default 35) so final_yield_kg_m2 is actually nonzero.
    body = client.post("/simulate", json={"duration_days": 60}).json()
    summary = body["summary"]
    assert summary["ber_yield_loss_fraction"] == 0.0
    assert summary["recipe_adequacy_multiplier"] == pytest.approx(1.0)
    assert summary["ec_adjusted_final_yield_kg_m2"] < summary["final_yield_kg_m2"]
    assert summary["marketable_yield_kg_m2"] == pytest.approx(summary["ec_adjusted_final_yield_kg_m2"])


def test_marketable_yield_kg_m2_matches_hand_computed_formula():
    body = client.post("/simulate", json={"duration_days": 5}).json()
    summary = body["summary"]
    config = client.get("/config").json()["hydroponic"]

    effective_dry_matter_ratio = 1.0 + config["ec_dry_matter_slope_per_ms_cm"] * (
        config["ec_target_ms_cm"] - config["ec_dry_matter_reference_ms_cm"]
    )
    expected_ec_adjusted = summary["final_yield_kg_m2"] / effective_dry_matter_ratio
    assert summary["ec_adjusted_final_yield_kg_m2"] == pytest.approx(expected_ec_adjusted, rel=1e-6)

    expected_marketable = (
        expected_ec_adjusted * (1.0 - summary["ber_yield_loss_fraction"]) * summary["recipe_adequacy_multiplier"]
    )
    assert summary["marketable_yield_kg_m2"] == pytest.approx(expected_marketable, rel=1e-6)
    assert summary["total_marketable_yield_kg"] == pytest.approx(
        summary["marketable_yield_kg_m2"] * summary["area_m2"], rel=1e-6
    )


def test_recirculation_electricity_is_bounded_by_its_fixed_fan_power():
    body = client.post("/simulate", json={"duration_days": 5}).json()
    summary = body["summary"]
    # recirculation_fan_power_kw default (config/greenhouse_example.yaml) is 4.7 kW, fixed --
    # the recirculation fans are either fully on or off, never modulated -- so total kWh can
    # never exceed running the whole period at that constant power.
    max_possible_kwh = 4.7 * 5 * 24
    assert 0 < summary["total_recirculation_elec_kwh"] <= max_possible_kwh


def test_truss_rate_is_consistent_with_final_yield_and_config_defaults():
    body = client.post("/simulate", json={"duration_days": 30}).json()
    summary = body["summary"]
    config = client.get("/config").json()
    fruit_weight_g = config["crop"]["target_fruit_weight_g"]
    fruits_per_truss = config["crop"]["fruits_per_truss"]
    density = config["crop"]["density_plants_per_m2"]
    stems_per_plant = config["crop"]["stems_per_plant"]
    stem_density = density * stems_per_plant

    expected_trusses_per_stem = (
        summary["final_yield_kg_m2"] * 1000.0 / stem_density / (fruit_weight_g * fruits_per_truss)
    )
    assert summary["final_trusses_per_stem"] == pytest.approx(expected_trusses_per_stem)
    assert summary["avg_truss_rate_per_week"] == pytest.approx(
        summary["final_trusses_per_stem"] / (30 / 7.0)
    )


def test_steady_state_truss_rate_is_none_when_run_shorter_than_full_production_start():
    # default config: fruiting_start_days=35 + fruiting_ramp_days=20 = day 55
    body = client.post("/simulate", json={"duration_days": 30}).json()
    summary = body["summary"]
    assert summary["full_production_start_day"] == 55
    assert summary["steady_state_truss_rate_per_week"] is None


def test_steady_state_truss_rate_excludes_the_diluting_startup_phase():
    body = client.post("/simulate", json={"duration_days": 150}).json()
    summary = body["summary"]
    config = client.get("/config").json()
    fruit_weight_g = config["crop"]["target_fruit_weight_g"]
    fruits_per_truss = config["crop"]["fruits_per_truss"]
    stem_density = config["crop"]["density_plants_per_m2"] * config["crop"]["stems_per_plant"]
    full_production_start_day = summary["full_production_start_day"]

    yield_at_boundary = body["daily_series"][full_production_start_day - 1]["fruit_fresh_yield_kg_m2"]
    steady_state_days = summary["duration_days"] - full_production_start_day
    expected_trusses_per_stem = (
        (summary["final_yield_kg_m2"] - yield_at_boundary)
        * 1000.0
        / stem_density
        / (fruit_weight_g * fruits_per_truss)
    )
    expected_rate = expected_trusses_per_stem / (steady_state_days / 7.0)
    # yield_at_boundary comes from daily_series, which rounds to 3 decimals for display --
    # a looser tolerance than the default absorbs that rounding, not a real mismatch.
    assert summary["steady_state_truss_rate_per_week"] == pytest.approx(expected_rate, rel=1e-4)

    # the startup/ramp phase runs at near-zero production, so excluding it should raise the rate
    # relative to the whole-season average (which is diluted by that near-zero window)
    assert summary["steady_state_truss_rate_per_week"] > summary["avg_truss_rate_per_week"]


def test_avg_fruit_set_pct_is_within_0_and_100():
    body = client.post("/simulate", json={"duration_days": 10}).json()
    assert 0.0 <= body["summary"]["avg_fruit_set_pct"] <= 100.0


def test_stricter_dehumidification_setpoint_increases_its_electricity_use():
    loose = client.post(
        "/simulate", json={"duration_days": 10, "dehumidification_setpoint_pct": 85}
    ).json()["summary"]
    strict = client.post(
        "/simulate", json={"duration_days": 10, "dehumidification_setpoint_pct": 60}
    ).json()["summary"]
    assert strict["total_dehumidification_elec_kwh"] > loose["total_dehumidification_elec_kwh"]


# -- /weather_preview: lightweight preview for the weather tab, no climate/crop model --


def test_weather_preview_with_no_overrides_uses_backend_config_defaults():
    response = client.get("/weather_preview")
    assert response.status_code == 200
    body = response.json()
    assert "daily_series" in body
    row = body["daily_series"][0]
    assert "date" in row
    assert "temp_out_c" in row
    assert "solar_rad_w_m2" in row


def test_weather_preview_duration_override_shortens_the_series():
    response = client.get("/weather_preview", params={"duration_days": 5})
    assert response.status_code == 200
    assert len(response.json()["daily_series"]) == 5


def test_weather_preview_start_date_override_is_reflected():
    response = client.get("/weather_preview", params={"start_date": "2027-01-01", "duration_days": 2})
    assert response.status_code == 200
    body = response.json()
    assert body["daily_series"][0]["date"] == "2027-01-01"
