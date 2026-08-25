# Trends in CO2 — NOAA Global Monitoring Laboratory

- **Publisher:** NOAA Global Monitoring Laboratory (Mauna Loa Observatory record)
- **URL:** https://gml.noaa.gov/ccgg/trends/
- **Type:** Government scientific data page (continuously updated, not paginated)
- **Retrieved:** 2026-08-19, via web search
- **Used for:** `climate_control.co2_ambient_ppm` (config/greenhouse_example.yaml) — this is a **factual current value**, not a modeling assumption to recalibrate.

## Data found

> Global average atmospheric CO2 was 422.8 ppm in 2024 (new record high). Seasonal peak exceeded 430 ppm at Mauna Loa in May 2025 (430.5 ppm average). May 2025 Scripps monthly average: 430.2 ppm.

**Note for next update:** the config currently uses `420.0` ppm. Given the trend above (422.8 ppm annual average for 2024, climbing further into 2025), `420` is now slightly stale — a figure closer to **424–426 ppm** would better reflect the current annual-average level as of 2026. Not changed in this pass since it wasn't asked; flagging for whoever next touches `climate_control.co2_ambient_ppm`.
