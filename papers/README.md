# Papers — source citation cards

One file per source used in `docs/assumptions/`. This session's sandboxed environment blocks direct internet access (only a search API is reachable, not arbitrary URL fetches or downloads) — so these are **citation cards**, not saved PDFs: title, publisher, URL, retrieval date, and the excerpt that was actually used to justify a parameter value. Full PDFs are *not* stored here.

**If you want a local PDF copy:** open the URL in the citation card and save it yourself (browser "Print to PDF" or the site's download button) — drop it in this folder next to its citation card, same filename with `.pdf` instead of `.md`. Several of these sit behind ResearchGate/ScienceDirect logins that a plain fetch can't get past anyway, so a manual download is often the only way to get the actual PDF regardless of this environment's restrictions.

**Naming convention:** `<short-slug>.md`, referenced by that slug from `docs/assumptions/*.md` and from `docs/assumptions/sources.xlsx`.

| File | Used for |
|---|---|
| [`greenhousemag-heat-loss.md`](./greenhousemag-heat-loss.md) | `cover_u_value_w_m2k` |
| [`ugi-chp-overview.md`](./ugi-chp-overview.md) | `heat_to_power_ratio` |
| [`vt-extension-spes-474.md`](./vt-extension-spes-474.md) | `density_plants_per_m2`, `reference_density_plants_per_m2` |
| [`peet-welles-greenhouse-tomato-production.md`](./peet-welles-greenhouse-tomato-production.md) | `density_plants_per_m2`, `reference_density_plants_per_m2` |
| [`researchgate-323225604-temp-vpd-review.md`](./researchgate-323225604-temp-vpd-review.md) | `heating_setpoint_day_c`, `heating_setpoint_night_c`, `co2_setpoint_day_ppm`, `T_OPT_C` |
| [`researchgate-258515123-photosynthesis-ec.md`](./researchgate-258515123-photosynthesis-ec.md) | `P_MAX_UMOL_M2_LEAF_S` |
| [`frontiers-2017-00365-heat-photosynthesis.md`](./frontiers-2017-00365-heat-photosynthesis.md) | `T_OPT_C` |
| [`bertin-gary-1993-tomgro.md`](./bertin-gary-1993-tomgro.md) | `fruit_partition_fraction_max` |
| [`noaa-mauna-loa-co2.md`](./noaa-mauna-loa-co2.md) | `co2_ambient_ppm` |
| [`usda-fdc-tomato-170457.md`](./usda-fdc-tomato-170457.md) | `dry_matter_content_fruit` |
| [`geothermiki-s192g-quote.md`](./geothermiki-s192g-quote.md) | `geometry.height_m`, `geometry.cover_area_factor` — real vendor quote for this greenhouse |
| [`tunnelvisionhoops-double-layer.md`](./tunnelvisionhoops-double-layer.md) | `geometry.cover_u_value_w_m2k` |
| [`greenhouse-film-180micron-transmission.md`](./greenhouse-film-180micron-transmission.md) | `geometry.cover_transmissivity` |
| [`tomato-canopy-extinction-coefficient.md`](./tomato-canopy-extinction-coefficient.md) | `CANOPY_LIGHT_EXTINCTION_COEFF` |
| [`tomato-transpiration-latent-heat-fraction.md`](./tomato-transpiration-latent-heat-fraction.md) | `TRANSPIRATION_ENERGY_FRACTION` |
| [`tomato-vpd-optimal-range.md`](./tomato-vpd-optimal-range.md) | `VPD_MIN_KPA`, `VPD_OPT_KPA`, `VPD_MAX_KPA` |
| [`greenhouse-condensation-dewpoint-physics.md`](./greenhouse-condensation-dewpoint-physics.md) | condensation mechanism in `twin/climate_model.py` |
| [`greenhouse-tomato-optimal-rh.md`](./greenhouse-tomato-optimal-rh.md) | `climate_control.dehumidification_setpoint_pct` |
| [`tomato-co2-optimum-700ppm.md`](./tomato-co2-optimum-700ppm.md) | `CO2_SATURATION_PPM`, `climate_control.co2_setpoint_day_ppm` |
| [`co2-half-saturation-tomato.md`](./co2-half-saturation-tomato.md) | `CO2_HALF_SAT_PPM` |
| [`co2-lai-growth-boost.md`](./co2-lai-growth-boost.md) | `CO2_LAI_BOOST_MAX`, `CO2_AMBIENT_REFERENCE_PPM` |
| [`thermal-screen-automatic-control-logic.md`](./thermal-screen-automatic-control-logic.md) | Screen deploy/retract logic, `chp_heat_margin_fraction`, `VENT_RAMP_BAND_C` reuse — user-specified control logic, not a literature source |
| [`open-meteo-historical-weather-api.md`](./open-meteo-historical-weather-api.md) | `weather.source: csv_typical_year` — real weather data source for Αλεξάνδρεια Ημαθίας (script written, not yet run) |
| [`fan-pad-evaporative-cooling.md`](./fan-pad-evaporative-cooling.md) | `climate_control.fan_pad_efficiency`, `_wet_bulb_temp_c` |
| [`canopy-self-shading-photosynthesis.md`](./canopy-self-shading-photosynthesis.md) | `_canopy_light_response` — Beer-Lambert-integrated canopy photosynthesis fix |
| [`tomato-fruit-set-temperature-sensitivity.md`](./tomato-fruit-set-temperature-sensitivity.md) | `FRUIT_SET_T_MIN_C`, `FRUIT_SET_T_OPT_C`, `FRUIT_SET_T_MAX_C` |

See [`docs/assumptions/sources.xlsx`](../docs/assumptions/sources.xlsx) for the full table (variable, code variable, explanation, source) in one spreadsheet.
