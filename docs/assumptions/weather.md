# Weather assumptions

`config/greenhouse_example.yaml` → `weather:` block. Model code: `twin/weather.py`.

## Active source: real "typical year" for Αλεξάνδρεια Ημαθίας (`csv_typical_year`)

As of 2026-08-24, `weather.source` is `"csv_typical_year"`, backed by `config/weather/alexandreia-imathias-typical-year.csv` — **real** hourly weather, not synthetic. 10 years (2015–2024) of `temperature_2m`, `relative_humidity_2m`, `shortwave_radiation` for Αλεξάνδρεια Ημαθίας (40.63°N, 22.47°E), fetched from the [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api) (free, no API key, CC BY 4.0 attribution) via `scripts/fetch_weather.py`, averaged per (month, day, hour) into a repeatable "typical year" — see `twin/weather.py`'s module docstring for why a typical year rather than exact historical dates (simulations here run against future planting dates real history can't cover directly). Full methodology and licensing notes: `papers/open-meteo-historical-weather-api.md`.

**How it was actually fetched:** this project's own sandboxed dev session can't reach external hosts (`archive-api.open-meteo.com` returns `EGRESS_BLOCKED` on both a direct request and the WebFetch tool) — the data was pulled by manually running the **"Fetch weather data"** GitHub Actions workflow (`.github/workflows/fetch-weather.yml`, runs on a GitHub-hosted runner with normal internet access and commits the CSV automatically). The fetch itself needed retry logic (`scripts/fetch_weather.py`): the first run hit a TLS handshake timeout on one of 10 per-year requests: consolidated to 5 two-year chunks with up to 5 retries (exponential backoff) each, which then succeeded.

**Real-data finding, 2026-08-24:** switching from synthetic to real weather noticeably changed the simulation, not just cosmetically — outdoor temperature ranges from -0.5°C to 30.4°C across the typical year (vs. the synthetic generator's smoother sinusoid), and on the coldest real nights **indoor temperature drops to ~3.9°C**, well below the 17°C night setpoint — the CHP's fixed 1150 kW heat output is not actually sufficient to hold setpoint on the coldest real nights at this site. 150-day run: yield 15.55 → 14.11 kg/m², total heat consumption 391,456 → 544,977 kWh (up ~39%), screen deployed 54% → 71% of hours. This is a genuine finding about the real site/CHP sizing, not a bug — flagged here rather than acted on, since it's a design/business decision (bigger CHP? accept colder night setpoints in practice? supplemental heating?) for the user, not something to silently fix in the model.

**Known limitation of the "typical year" averaging** (discussed with the user, not fixed): averaging per (month, day, hour) across 10 years blends together clear, cold nights (radiative cooling — no cloud cover to trap outgoing longwave radiation, the physically coldest real nights) with milder cloudy nights on the same calendar date. So even this real-data typical year likely still *understates* how cold the single coldest real nights get, and by extension may understate how far short of setpoint the CHP actually falls in the worst case. Not pursued further for now (2026-08-24) — worth revisiting if CHP sizing becomes a live decision.

## Fallback source: synthetic generator (`source: "synthetic"`)

Kept as a fallback/default-config option, no longer active for this site. A pure sine-wave generator (seasonal + diurnal cosine curves) with **no randomness and no real site data** — every run with the same `start_date`/`duration_days` produces bit-identical weather.

| Parameter | Value | Tag | Notes |
|---|---|---|---|
| `latitude_deg` | 40.63 (was 37.9/Athens, corrected 2026-08-24) | **SITE-SPECIFIC** | Αλεξάνδρεια Ημαθίας's real latitude — still unused by any model math (see "Known gap" below), kept correct for when/if that changes. |
| `mean_annual_temp_c` | 18.0 | **PLACEHOLDER** | Athens/Attica-plausible, not the real site's actual average — only feeds the synthetic generator, unused while `source: csv_typical_year`. |
| `seasonal_amplitude_c` | 9.0 | **PLACEHOLDER** | Same — unused while `source: csv_typical_year`. |
| `diurnal_amplitude_c` | 6.0 | **PLACEHOLDER** | Same — unused while `source: csv_typical_year`. |
| `peak_solar_w_m2` | 850.0 | **PLACEHOLDER** | Same — unused while `source: csv_typical_year`. |

## Known gap (not a numeric assumption, a modeling gap)

`latitude_deg` is stored but not actually used to compute solar geometry (day length, sun angle) by either weather source — the synthetic generator uses flat calendar-day/hour sinusoids, and the real `csv_typical_year` source just replays measured radiation directly (which already has real sun-angle effects baked in, so this gap only really applies to the synthetic fallback).
