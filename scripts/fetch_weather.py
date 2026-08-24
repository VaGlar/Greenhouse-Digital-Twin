"""Fetch real historical weather for a site from Open-Meteo and build a
"typical year" CSV the model can read via weather.source: "csv_typical_year".

Open-Meteo's Historical Weather API (https://open-meteo.com/en/docs/historical-weather-api)
is free, requires no API key, and is licensed for non-commercial use (CC BY 4.0
attribution to Open-Meteo / the underlying reanalysis datasets) -- see their site
for commercial licensing if this greenhouse's use ever becomes commercial.

Run this once, from an environment with normal internet access -- this
repo's own sandboxed dev session cannot reach external hosts. Two ways:

  - GitHub Actions: run the "Fetch weather data" workflow manually
    (.github/workflows/fetch-weather.yml, Actions tab -> Run workflow).
    It runs this script on a GitHub-hosted runner and commits the result
    automatically -- no local setup needed.
  - Locally / in a Codespace terminal: `python scripts/fetch_weather.py`

It writes config/weather/alexandreia-imathias-typical-year.csv. After that,
switch config/greenhouse_example.yaml's weather block to:

    weather:
      source: csv_typical_year
      csv_path: config/weather/alexandreia-imathias-typical-year.csv

Why a "typical year" instead of exact historical dates: simulations here
commonly run against future planting dates (e.g. 2026-09-15) that real
historical data can't cover directly. Averaging several years of history per
(month, day, hour) gives a realistic seasonal/diurnal profile for the real
site that can be replayed against any simulation start date -- see
twin/weather.py's _load_csv_typical_year.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

# Alexandreia, Imathia, Greece.
LATITUDE = 40.63
LONGITUDE = 22.47
TIMEZONE = "Europe/Athens"

# 10 full calendar years of history -- long enough to average out one-off
# extreme years, short enough to fetch quickly and stay clear of any recent
# incomplete year.
START_YEAR = 2015
END_YEAR = 2024
# Years per request -- fewer, larger requests instead of one per year, so a
# single transient network hiccup (e.g. a TLS handshake timeout, seen on a
# GitHub Actions run 2026-08-24) can't fail the whole fetch by itself; each
# chunk also gets its own retries below.
YEARS_PER_CHUNK = 2

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "config" / "weather" / "alexandreia-imathias-typical-year.csv"

ARCHIVE_API_URL = "https://archive-api.open-meteo.com/v1/archive"
HOURLY_VARS = "temperature_2m,relative_humidity_2m,shortwave_radiation"

MAX_ATTEMPTS = 5
REQUEST_TIMEOUT_S = 120


def _fetch_range(start_year: int, end_year: int) -> pd.DataFrame:
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "start_date": f"{start_year}-01-01",
        "end_date": f"{end_year}-12-31",
        "hourly": HOURLY_VARS,
        "timezone": TIMEZONE,
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{ARCHIVE_API_URL}?{query}"

    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            print(f"Fetching {start_year}-{end_year} (attempt {attempt}/{MAX_ATTEMPTS})...")
            with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT_S) as response:
                payload = json.loads(response.read())
            hourly = payload["hourly"]
            return pd.DataFrame(
                {
                    "timestamp": pd.to_datetime(hourly["time"]),
                    "temp_out_c": hourly["temperature_2m"],
                    "rh_out_pct": hourly["relative_humidity_2m"],
                    "solar_rad_w_m2": hourly["shortwave_radiation"],
                }
            )
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_error = e
            wait_s = 2**attempt  # 2, 4, 8, 16, 32
            print(f"  failed ({e}); retrying in {wait_s}s")
            if attempt < MAX_ATTEMPTS:
                time.sleep(wait_s)

    raise RuntimeError(f"Failed to fetch {start_year}-{end_year} after {MAX_ATTEMPTS} attempts") from last_error


def main() -> None:
    chunks = [
        _fetch_range(y, min(y + YEARS_PER_CHUNK - 1, END_YEAR))
        for y in range(START_YEAR, END_YEAR + 1, YEARS_PER_CHUNK)
    ]
    all_years = pd.concat(chunks, ignore_index=True)

    all_years["month"] = all_years["timestamp"].dt.month
    all_years["day"] = all_years["timestamp"].dt.day
    all_years["hour"] = all_years["timestamp"].dt.hour

    typical_year = (
        all_years.groupby(["month", "day", "hour"], as_index=False)
        .agg(
            temp_out_c=("temp_out_c", "mean"),
            solar_rad_w_m2=("solar_rad_w_m2", "mean"),
            rh_out_pct=("rh_out_pct", "mean"),
        )
        .sort_values(["month", "day", "hour"])
    )
    # Radiation can't average out negative from noisy nighttime near-zero readings.
    typical_year["solar_rad_w_m2"] = typical_year["solar_rad_w_m2"].clip(lower=0.0)
    typical_year["rh_out_pct"] = typical_year["rh_out_pct"].clip(lower=0.0, upper=100.0)

    for col in ("temp_out_c", "solar_rad_w_m2", "rh_out_pct"):
        typical_year[col] = typical_year[col].round(2)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    typical_year.to_csv(OUTPUT_PATH, index=False)
    print(f"Wrote {len(typical_year)} rows ({START_YEAR}-{END_YEAR} average) to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
