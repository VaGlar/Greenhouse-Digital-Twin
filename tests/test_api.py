"""Tests for the FastAPI layer (api/main.py).

Uses small duration_days overrides everywhere a simulation actually needs to
run, so the suite stays fast -- the physics itself is covered by
test_climate_model.py / test_crop_model.py / test_weather.py, not here.
"""

from __future__ import annotations

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
        "co2_ambient_ppm",
        "max_co2_available_ppm",
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
