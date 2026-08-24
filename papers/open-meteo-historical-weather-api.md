# Open-Meteo Historical Weather API — real weather data source for Αλεξάνδρεια Ημαθίας

- **Type:** Free public API, no key required (ERA5/ERA5-Land reanalysis + station blend), CC BY 4.0 attribution required
- **URL:** https://open-meteo.com/en/docs/historical-weather-api
- **Retrieved:** 2026-08-24 (script written; not yet run — see below)
- **Used for:** `weather.source: csv_typical_year`, `config/weather/alexandreia-imathias-typical-year.csv` (twin/weather.py, scripts/fetch_weather.py)

## Why this source

The user asked about pulling real weather data for Αλεξάνδρεια Ημαθίας (40.63°N, 22.47°E) from Wunderground or WeatherSpark. Neither is practical to fetch programmatically: Wunderground's historical API is paywalled (subscription required), and WeatherSpark is a visualization layer over other datasets (mainly NOAA/ERA5) with no bulk-download API of its own. Open-Meteo's Historical Weather API is free, requires no API key, is licensed for non-commercial use, and returns hourly `temperature_2m`, `relative_humidity_2m`, and `shortwave_radiation` for any lat/lon back to 1940 — a direct match for this model's `temp_out_c`/`rh_out_pct`/`solar_rad_w_m2` inputs.

## What was fetched (methodology, not a specific data excerpt)

`scripts/fetch_weather.py` pulls 10 full years (2015–2024) of hourly data for Αλεξάνδρεια Ημαθίας and averages every (month, day, hour) across those years into a repeatable "typical year" template — see `docs/assumptions/weather.md` for why (simulations here run against future planting dates that exact historical dates can't cover). This is a methodology decision, not a numeric fact to cite — the actual averaged values live in the generated CSV, not in this card.

## Access note

This project's own sandboxed dev session could not reach `archive-api.open-meteo.com` directly (network egress allowlist) — confirmed with both a direct HTTPS request and the WebFetch tool, both returned `EGRESS_BLOCKED`. The fetch script is written to be run by the user from an environment with normal internet access (e.g. the GitHub Codespace itself).

## Licensing note

Open-Meteo's data is free for non-commercial use under CC BY 4.0 (attribution required). If this greenhouse's use of the twin ever becomes commercial, check https://open-meteo.com/en/pricing for their commercial terms before continuing to use this data source.
