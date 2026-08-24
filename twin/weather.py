"""External weather input.

Supports three sources:
  - "csv": historical hourly weather from a local CSV file, matched by exact
            calendar date (columns: timestamp, temp_out_c, solar_rad_w_m2,
            rh_out_pct) -- for real historical data covering the exact dates
            being simulated.
  - "csv_typical_year": a real-site "typical year" built by averaging several
            years of historical data per (month, day, hour) -- see
            scripts/fetch_weather.py. Looked up cyclically by calendar
            month/day/hour regardless of which actual year the simulation's
            start_date falls in, since simulations commonly run against
            future planting dates that real historical data can't cover
            directly (columns: month, day, hour, temp_out_c, solar_rad_w_m2,
            rh_out_pct).
  - "synthetic": a seasonal + diurnal sinusoidal generator, used when no
            real weather data is available yet for the target site.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta

import pandas as pd

from twin.params import WeatherParams


@dataclass
class WeatherPoint:
    timestamp: datetime
    temp_out_c: float
    solar_rad_w_m2: float
    rh_out_pct: float


def load_weather(params: WeatherParams, start_date: date, duration_days: int, timestep_hours: float) -> pd.DataFrame:
    if params.source == "csv":
        return _load_csv(params, start_date, duration_days)
    if params.source == "csv_typical_year":
        return _load_csv_typical_year(params, start_date, duration_days, timestep_hours)
    if params.source == "synthetic":
        return _generate_synthetic(params, start_date, duration_days, timestep_hours)
    raise ValueError(f"Unknown weather source: {params.source!r}")


def _load_csv(params: WeatherParams, start_date: date, duration_days: int) -> pd.DataFrame:
    if not params.csv_path:
        raise ValueError("weather.csv_path is required when weather.source == 'csv'")
    df = pd.read_csv(params.csv_path, parse_dates=["timestamp"])
    required = {"timestamp", "temp_out_c", "solar_rad_w_m2", "rh_out_pct"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"weather CSV is missing required columns: {sorted(missing)}")

    end_date = start_date + timedelta(days=duration_days)
    mask = (df["timestamp"].dt.date >= start_date) & (df["timestamp"].dt.date < end_date)
    df = df.loc[mask].sort_values("timestamp").reset_index(drop=True)
    if df.empty:
        raise ValueError(
            f"weather CSV {params.csv_path!r} has no rows covering "
            f"{start_date} .. {end_date}"
        )
    return df


def _load_csv_typical_year(
    params: WeatherParams, start_date: date, duration_days: int, timestep_hours: float
) -> pd.DataFrame:
    if not params.csv_path:
        raise ValueError("weather.csv_path is required when weather.source == 'csv_typical_year'")
    template = pd.read_csv(params.csv_path)
    required = {"month", "day", "hour", "temp_out_c", "solar_rad_w_m2", "rh_out_pct"}
    missing = required - set(template.columns)
    if missing:
        raise ValueError(f"typical-year weather CSV is missing required columns: {sorted(missing)}")
    template = template.set_index(["month", "day", "hour"])

    n_steps = int(duration_days * 24 / timestep_hours)
    start_dt = datetime.combine(start_date, datetime.min.time())

    rows = []
    for i in range(n_steps):
        ts = start_dt + timedelta(hours=i * timestep_hours)
        key = (ts.month, ts.day, ts.hour)
        if key not in template.index:
            # Feb 29 in a simulation year that's a leap year, but no leap year
            # in the fetched history had that date -- fall back to Feb 28.
            key = (ts.month, 28, ts.hour) if ts.month == 2 and ts.day == 29 else key
        row = template.loc[key]
        rows.append(
            WeatherPoint(
                timestamp=ts,
                temp_out_c=float(row["temp_out_c"]),
                solar_rad_w_m2=float(row["solar_rad_w_m2"]),
                rh_out_pct=float(row["rh_out_pct"]),
            )
        )

    return pd.DataFrame([r.__dict__ for r in rows])


def _generate_synthetic(
    params: WeatherParams, start_date: date, duration_days: int, timestep_hours: float
) -> pd.DataFrame:
    n_steps = int(duration_days * 24 / timestep_hours)
    start_dt = datetime.combine(start_date, datetime.min.time())

    rows = []
    for i in range(n_steps):
        ts = start_dt + timedelta(hours=i * timestep_hours)
        day_of_year = ts.timetuple().tm_yday
        hour = ts.hour + ts.minute / 60.0

        # Seasonal cycle: peaks around day 172 (Jun 21, NH summer solstice).
        seasonal = math.cos(2 * math.pi * (day_of_year - 172) / 365.25)
        # Diurnal cycle: peaks in early afternoon (~14:00), trough before dawn.
        diurnal = math.cos(2 * math.pi * (hour - 14) / 24)

        temp_out_c = params.mean_annual_temp_c + params.seasonal_amplitude_c * seasonal + params.diurnal_amplitude_c * diurnal

        # Solar radiation: zero at night, bell-shaped during daylight, scaled
        # by the seasonal factor (less winter sun) and clipped at zero.
        daylight = max(0.0, math.cos(2 * math.pi * (hour - 12) / 24))
        seasonal_solar_factor = max(0.15, 0.5 + 0.5 * seasonal)
        solar_rad_w_m2 = params.peak_solar_w_m2 * seasonal_solar_factor * daylight

        rh_out_pct = 65.0 - 10.0 * daylight  # slightly drier at midday, simplistic

        rows.append(
            WeatherPoint(
                timestamp=ts,
                temp_out_c=temp_out_c,
                solar_rad_w_m2=solar_rad_w_m2,
                rh_out_pct=rh_out_pct,
            )
        )

    return pd.DataFrame([r.__dict__ for r in rows])
