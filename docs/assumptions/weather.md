# Weather assumptions

`config/greenhouse_example.yaml` → `weather:` block. Model code: `twin/weather.py`.

**This entire section is the lowest-confidence part of the twin** — it's explicitly a synthetic placeholder, not real weather data, and the code already says so (`weather.py` docstring: `"synthetic"` source is *"used when no real historical data is available yet for the target site"*).

| Parameter | Value | Tag | Notes |
|---|---|---|---|
| `source` | "synthetic" | **PLACEHOLDER by design** | Sine-wave generator (seasonal + diurnal cosine curves), not measured weather. The code already supports switching to `source: "csv"` with a real historical hourly weather file — this is the single highest-value real-data upgrade available for the whole project, since every other model (climate, crop) runs on top of whatever this produces. |
| `latitude_deg` | 37.9 | **SITE-SPECIFIC** | Athens' latitude — a reasonable stand-in only if the real greenhouse is near Athens; update to the actual site's latitude (used nowhere in the current synthetic generator's math, currently just informational — see note below). |
| `mean_annual_temp_c` | 18.0 | **SITE-SPECIFIC, plausible for Greece** | Roughly matches Athens/Attica's average annual temperature (Greek National Meteorological Service / Köppen climate data for the region generally cites ~17–19°C annual mean). Reasonable placeholder if the greenhouse is in a similar climate zone; must be replaced with the real site's average once known. |
| `seasonal_amplitude_c` | 9.0 | **PLACEHOLDER** | Not checked against a specific climate dataset for the target region — plausible order of magnitude for a Mediterranean climate's summer/winter swing, not verified. |
| `diurnal_amplitude_c` | 6.0 | **PLACEHOLDER** | Same — plausible day/night swing, not verified against real station data. |
| `peak_solar_w_m2` | 850.0 | **PLACEHOLDER, plausible** | Peak clear-sky solar radiation for Mediterranean latitudes is commonly in the 800–1000 W/m² range at solar noon in summer — 850 is a reasonable placeholder, not individually sourced to a specific irradiance dataset for the target site. |

## Known gap (not a numeric assumption, a modeling gap)

`latitude_deg` is currently stored but not actually used to compute solar geometry (day length, sun angle) — the synthetic generator uses flat calendar-day/hour sinusoids instead. So changing latitude today has no effect on the simulation. This should be flagged if/when latitude-driven daylight length becomes important (e.g. for a real site far from Athens' latitude).

## What actually matters here

Once real historical weather (or even a nearby official weather station's hourly CSV export) is available for the actual greenhouse site, switching `weather.source` to `"csv"` replaces this entire file's worth of assumptions in one config change — no code changes needed. This is the cheapest, highest-impact accuracy improvement available for the whole twin.
