from datetime import date

import pandas as pd

from twin.params import WeatherParams
from twin.weather import load_weather


def _write_template(tmp_path, rows):
    path = tmp_path / "typical_year.csv"
    pd.DataFrame(rows, columns=["month", "day", "hour", "temp_out_c", "solar_rad_w_m2", "rh_out_pct"]).to_csv(
        path, index=False
    )
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
