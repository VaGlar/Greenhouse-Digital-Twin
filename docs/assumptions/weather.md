# Weather assumptions

`config/greenhouse_example.yaml` → `weather:` block. Model code: `twin/weather.py`.

## Active source: real "typical year" for Αλεξάνδρεια Ημαθίας (`csv_typical_year`)

As of 2026-08-24, `weather.source` is `"csv_typical_year"`, backed by `config/weather/alexandreia-imathias-typical-year.csv` — **real** hourly weather, not synthetic. 10 years (2015–2024) of `temperature_2m`, `relative_humidity_2m`, `shortwave_radiation` for Αλεξάνδρεια Ημαθίας (40.63°N, 22.47°E), fetched from the [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api) (free, no API key, CC BY 4.0 attribution) via `scripts/fetch_weather.py`, averaged per (month, day, hour) into a repeatable "typical year" — see `twin/weather.py`'s module docstring for why a typical year rather than exact historical dates (simulations here run against future planting dates real history can't cover directly). Full methodology and licensing notes: `papers/open-meteo-historical-weather-api.md`.

**How it was actually fetched:** this project's own sandboxed dev session can't reach external hosts (`archive-api.open-meteo.com` returns `EGRESS_BLOCKED` on both a direct request and the WebFetch tool) — the data was pulled by manually running the **"Fetch weather data"** GitHub Actions workflow (`.github/workflows/fetch-weather.yml`, runs on a GitHub-hosted runner with normal internet access and commits the CSV automatically). The fetch itself needed retry logic (`scripts/fetch_weather.py`): the first run hit a TLS handshake timeout on one of 10 per-year requests: consolidated to 5 two-year chunks with up to 5 retries (exponential backoff) each, which then succeeded.

**Real-data finding, 2026-08-24:** switching from synthetic to real weather noticeably changed the simulation, not just cosmetically — outdoor temperature ranges from -0.5°C to 30.4°C across the typical year (vs. the synthetic generator's smoother sinusoid), and on the coldest real *daytime* hours **indoor temperature was seen dropping to ~3.9°C**, well below setpoint. **Correction, 2026-08-25:** this was initially (wrongly) attributed to the CHP's fixed 1150 kW heat output being insufficient. It wasn't — the CHP never exceeded 747 of its 1150 kW capacity in that run. The real cause was a ventilation overshoot bug (see `climate-control.md`'s `VENT_RAMP_BAND_C` entry): on cold-but-very-sunny hours, ventilation ramped up correctly but then removed a full hour's worth of heat in one uncorrected linear step, blowing straight through the setpoint and crashing indoor air all the way down to match outdoor air. Real weather is what actually exposed this (the synthetic generator's smoother, less extreme swings never combined enough cold + enough sun in one hour to trigger it) — a genuine case of real data surfacing a bug synthetic data had been masking. After the fix: min indoor temp 3.9°C → 15.6°C, daylight hours shaded by the screen 70% → 14%, 150-day yield 14.11 → **32.79 kg/m²** (a large jump, expected and correct: removing both the cold crashes and the excessive daytime shading unblocks a lot of previously-lost photosynthesis, not a new bug).

**Known limitation of the "typical year" averaging** (discussed with the user, not fixed): averaging per (month, day, hour) across 10 years blends together clear, cold nights (radiative cooling — no cloud cover to trap outgoing longwave radiation, the physically coldest real nights) with milder cloudy nights on the same calendar date. So this real-data typical year likely still *understates* how cold the single coldest real nights get. Not pursued further for now (2026-08-24) — worth revisiting if CHP sizing becomes a live decision (now a much lower-stakes question, since the ventilation fix shows the CHP has comfortable headroom in the typical-year scenario).

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
