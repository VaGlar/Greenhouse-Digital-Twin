from datetime import date, datetime, timedelta

import pandas as pd
import pytest

from twin.params import WeatherParams
from twin.weather import load_weather


def _write_template(tmp_path, rows):
    path = tmp_path / "typical_year.csv"
    pd.DataFrame(rows, columns=["month", "day", "hour", "temp_out_c", "solar_rad_w_m2", "rh_out_pct"]).to_csv(
        path, index=False
    )
    return str(path)


def _write_exact_date_csv(tmp_path, start, hours, temp_out_c=15.0, solar_rad_w_m2=200.0, rh_out_pct=60.0):
    path = tmp_path / "historical.csv"
    timestamps = [start + timedelta(hours=h) for h in range(hours)]
    pd.DataFrame(
        {
            "timestamp": timestamps,
            "temp_out_c": [temp_out_c] * hours,
            "solar_rad_w_m2": [solar_rad_w_m2] * hours,
            "rh_out_pct": [rh_out_pct] * hours,
        }
    ).to_csv(path, index=False)
    return str(path)


def test_csv_typical_year_looks_up_by_month_day_hour(tmp_path):
    rows = [(6, 15, h, 20.0 + h, 100.0 * h, 55.0) for h in range(24)]
    csv_path = _write_template(tmp_path, rows)
    params = WeatherParams(source="csv_typical_year", csv_path=csv_path)

    df = load_weather(params, start_date=date(2026, 6, 15), duration_days=1, timestep_hours=1.0)

    assert len(df) == 24
    assert df.iloc[3]["temp_out_c"] == 23.0  # hour 3 -> 20 + 3
    assert df.iloc[3]["solar_rad_w_m2"] == 300.0


def test_csv_typical_year_cycles_across_a_calendar_year_boundary(tmp_path):
    rows = [(12, 31, h, 5.0, 0.0, 80.0) for h in range(24)] + [(1, 1, h, -2.0, 0.0, 85.0) for h in range(24)]
    csv_path = _write_template(tmp_path, rows)
    params = WeatherParams(source="csv_typical_year", csv_path=csv_path)

    # Simulation starts Dec 31 of a real (future) year and rolls into Jan 1 of the next.
    df = load_weather(params, start_date=date(2026, 12, 31), duration_days=2, timestep_hours=1.0)

    assert len(df) == 48
    assert df.iloc[0]["temp_out_c"] == 5.0  # Dec 31
    assert df.iloc[24]["temp_out_c"] == -2.0  # Jan 1, wrapped correctly
    assert df.iloc[24]["timestamp"].year == 2027  # real calendar year still advances normally


def test_csv_typical_year_falls_back_to_feb_28_when_feb_29_is_missing(tmp_path):
    rows = [(2, 28, h, 10.0, 50.0, 60.0) for h in range(24)]
    csv_path = _write_template(tmp_path, rows)
    params = WeatherParams(source="csv_typical_year", csv_path=csv_path)

    # 2028 is a leap year, so the simulation's real calendar includes Feb 29,
    # but the fetched history (in this test) never had a leap year -- must fall back.
    df = load_weather(params, start_date=date(2028, 2, 29), duration_days=1, timestep_hours=1.0)

    assert len(df) == 24
    assert (df["temp_out_c"] == 10.0).all()


# -- "csv": exact-date historical weather --


def test_csv_exact_date_returns_only_rows_within_the_requested_window(tmp_path):
    csv_path = _write_exact_date_csv(tmp_path, datetime(2026, 1, 1), hours=24 * 5)
    params = WeatherParams(source="csv", csv_path=csv_path)

    df = load_weather(params, start_date=date(2026, 1, 2), duration_days=2, timestep_hours=1.0)

    assert len(df) == 48
    assert df["timestamp"].min() == datetime(2026, 1, 2)
    assert df["timestamp"].max() == datetime(2026, 1, 3, 23)


def test_csv_requires_csv_path():
    params = WeatherParams(source="csv", csv_path=None)
    with pytest.raises(ValueError, match="csv_path"):
        load_weather(params, start_date=date(2026, 1, 1), duration_days=1, timestep_hours=1.0)


def test_csv_rejects_missing_required_columns(tmp_path):
    path = tmp_path / "bad.csv"
    pd.DataFrame({"timestamp": [datetime(2026, 1, 1)], "temp_out_c": [10.0]}).to_csv(path, index=False)
    params = WeatherParams(source="csv", csv_path=str(path))

    with pytest.raises(ValueError, match="missing required columns"):
        load_weather(params, start_date=date(2026, 1, 1), duration_days=1, timestep_hours=1.0)


def test_csv_raises_when_no_rows_cover_the_requested_window(tmp_path):
    csv_path = _write_exact_date_csv(tmp_path, datetime(2026, 1, 1), hours=24)
    params = WeatherParams(source="csv", csv_path=csv_path)

    with pytest.raises(ValueError, match="no rows covering"):
        load_weather(params, start_date=date(2030, 1, 1), duration_days=1, timestep_hours=1.0)


# -- "synthetic": sinusoidal seasonal/diurnal generator (fallback with no real weather data) --


def test_synthetic_produces_one_row_per_hour():
    params = WeatherParams(source="synthetic")
    df = load_weather(params, start_date=date(2026, 3, 1), duration_days=3, timestep_hours=1.0)
    assert len(df) == 3 * 24


def test_synthetic_solar_radiation_is_zero_at_midnight_and_positive_at_midday():
    params = WeatherParams(source="synthetic", peak_solar_w_m2=800.0)
    df = load_weather(params, start_date=date(2026, 6, 21), duration_days=1, timestep_hours=1.0)
    assert df.iloc[0]["solar_rad_w_m2"] == 0.0  # hour 0 (midnight)
    assert df.iloc[13]["solar_rad_w_m2"] > 0.0  # hour 13, near the ~14:00 peak
    assert (df["solar_rad_w_m2"] >= 0.0).all()


def test_synthetic_summer_is_warmer_than_winter_at_the_same_hour():
    params = WeatherParams(source="synthetic", mean_annual_temp_c=15.0, seasonal_amplitude_c=10.0, diurnal_amplitude_c=0.0)
    summer = load_weather(params, start_date=date(2026, 6, 21), duration_days=1, timestep_hours=1.0)
    winter = load_weather(params, start_date=date(2026, 12, 21), duration_days=1, timestep_hours=1.0)
    assert summer.iloc[12]["temp_out_c"] > winter.iloc[12]["temp_out_c"]


# -- dispatch --


def test_load_weather_rejects_unknown_source():
    params = WeatherParams(source="not-a-real-source")
    with pytest.raises(ValueError, match="Unknown weather source"):
        load_weather(params, start_date=date(2026, 1, 1), duration_days=1, timestep_hours=1.0)
