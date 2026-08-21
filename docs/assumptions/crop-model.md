# Crop model assumptions

`config/greenhouse_example.yaml` → `crop:` block, plus module-level constants in `twin/crop_model.py`. This is the least-verified part of the whole twin — the module docstring already says *"illustrative, not a calibrated TOMGRO port"* — this file is the detailed version of that disclaimer.

## Config-level crop parameters

| Parameter | Value | Tag | Notes |
|---|---|---|---|
| `variety` | "Beefsteak tomato" | **SITE-SPECIFIC** | Placeholder variety name — real variety choice affects fruit weight, dry matter %, growth habit; not modeled per-variety yet. |
| `planting_date` | 2026-09-15 | **SITE-SPECIFIC** | Placeholder date, tied to `simulation.start_date`. |
| `density_plants_per_m2` | 2.5 | **SOURCED** | Standard commercial single-stem high-wire greenhouse tomato density is 2.3–2.5 plants/m², pushed toward ~3 with a second stem per plant. Sources: [Virginia Tech Extension SPES-474 — Plant density recommendations](https://www.pubs.ext.vt.edu/SPES/spes-474/spes-474.html); [Peet & Welles, "Greenhouse Tomato Production"](https://www.researchgate.net/profile/Arvind-Singh-21/post/How_much_maximum_yield_kg_m2_can_a_farmer_get_from_the_Tomato_crop_with_all_maximum_high_end_technology/attachment/59d6377e79197b8077994d54/AS:393263811973134@1470772807893/download/1.pdf) (book chapter PDF, specific page not identified — the 2.3 plants/m² figure is quoted in web summaries of this source, not confirmed against the original page). Confirmed 2026-08-19 after the user noticed the frontend's "optimal 3–4" slider band disagreed with this config value — that band was wrong, not the config; see `reference_density_plants_per_m2` below and the commit that fixed the slider. |
| `reference_density_plants_per_m2` | 2.5 | **SOURCED** | Set equal to `density_plants_per_m2` above deliberately — it's the density at which the model's canopy is assumed fully closed (`lai_max` reached). Same sources as above. |
| `lai_max` | 3.5 | **PLACEHOLDER** | Typical order-of-magnitude peak leaf area index for greenhouse tomato is often cited around 3–4, but this specific figure was not individually verified against a source — flagged for recalibration once real canopy measurements exist. |
| `lai_ramp_days` | 60 | **PLACEHOLDER** | Engineering guess for time-to-canopy-closure; not sourced. |
| `fruiting_start_days` | 35 | **PLACEHOLDER** | Days after planting before fruit set begins — plausible order of magnitude for indeterminate tomato but not individually sourced. |
| `fruiting_ramp_days` | 20 | **PLACEHOLDER** | Not sourced. |
| `fruit_partition_fraction_max` | 0.85 (raised from 0.6, 2026-08-19) | **SOURCED** | TOMGRO literature (Bertin & Gary, 1993, calibration/validation of TOMGRO for indeterminate greenhouse tomato) reports fruit growth accounting for **80–90%** of dry-matter/fresh-weight gain during peak fruiting. Raised to 0.85 (mid of that range) from the earlier 0.6 placeholder. Source: summaries of Bertin & Gary's TOMGRO validation work (via [ScienceDirect abstract](https://www.sciencedirect.com/science/article/abs/pii/S0305736496900098), page/table not individually confirmed). Baseline yield moved from 13.30 to 20.25 kg/m² (150-day run) as a result — combined with the T_OPT change below. |
| `dry_matter_content_fruit` | 0.055 | **SOURCED** | Ripe tomato fruit dry matter content is well documented in the 4–10% range depending on variety, with ~5.5% (USDA composition data: 94.5% water) a standard "average" figure. Source: USDA FoodData Central tomato composition data, referenced via general produce dry-matter guides. |

## `twin/crop_model.py` module-level constants

| Constant | Value | Tag | Notes |
|---|---|---|---|
| `P_MAX_UMOL_M2_LEAF_S` | 20.0 | **SOURCED, conservative end** | Light-saturated leaf photosynthesis rate for tomato is reported in the ~20–40 µmol CO2 m⁻²·s⁻¹ range across studies (varies by cultivar, EC, measurement conditions); one study specifically found 19.5–22.5 µmol·m⁻²·s⁻¹ depending on nutrient EC. 20 sits at the low-to-middle end of the range — a conservative, defensible choice. Source: [Growth and Photosynthetic Response of Tomato to Nutrient Solution Concentration at Two Light Levels](https://www.researchgate.net/publication/258515123_Growth_and_Photosynthetic_Response_of_Tomato_to_Nutrient_Solution_Concentration_at_Two_Light_Levels) (journal article, specific page not confirmed — figure taken from search-result summary). |
| `LIGHT_HALF_SAT_W_M2` | 200.0 | **PLACEHOLDER** | Not individually verified — a plausible order-of-magnitude light half-saturation constant, common in simplified canopy photosynthesis models, but not checked against a specific tomato citation. |
| `CO2_HALF_SAT_PPM` | 200.0 | **PLACEHOLDER** | Shape of the rising part of the CO2 response curve below its cap — not individually sourced. |
| `CO2_SATURATION_PPM` | 700.0 (added 2026-08-20) | **SOURCED, bug fix** | The raw Michaelis-Menten response (`co2/(co2+K)`) never caps — rises asymptotically forever, so yield kept increasing with CO2 setpoint with no limit (the user caught this directly: "however much I raise it, yield keeps rising — shouldn't 1200ppm be excessive?"). A study testing 500/700/850/1000 ppm on tomato found 700 ppm optimal, with no further yield benefit above it. Fixed by clamping the response function's input at 700 ppm — the curve plateaus there instead of climbing indefinitely. `climate_control.co2_setpoint_day_ppm` corrected from 900 to 700 to match (900 was spending CO2 dosing capacity for zero extra yield). Source: `papers/tomato-co2-optimum-700ppm.md`. Not addressed in this pass (holding for a separate discussion): whether `P_MAX_UMOL_M2_LEAF_S`/`CO2_HALF_SAT_PPM` should be jointly recalibrated now that this ceiling exists. |
| `T_MIN_C, T_OPT_C, T_MAX_C` | 10, 27 (raised from 24, 2026-08-19), 35 | **SOURCED** | *Photosynthetic* optimum for tomato is reported broader and higher than general growth optimum — "25–35°C, with 50% of photosynthetic rate retained even at 47°C" (tomato is more heat-tolerant photosynthetically than commonly assumed). T_OPT raised from 24°C to 27°C (within the 25-35°C reported optimum) to match. T_MIN (10°C) and T_MAX (35°C) left unchanged — general growth optimum literature (~15–32°C) supports T_MAX=35 and doesn't clearly contradict T_MIN=10, so those weren't touched in this pass. Source: [Sub-high Temperature and High Light Intensity effects on tomato photosynthesis](https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2017.00365/full) (Frontiers, open-access, specific page not applicable — HTML article) and [Review of optimum temperature for greenhouse tomato](https://www.researchgate.net/publication/323225604_Review_of_optimum_temperature_humidity_and_vapour_pressure_deficit_for_microclimate_evaluation_and_control_in_greenhouse_cultivation_of_tomato_a_review). |
| `MAINTENANCE_RESPIRATION_FRACTION_PER_DAY` | 0.015 | **PLACEHOLDER** | Not individually sourced — a plausible order-of-magnitude daily respiration loss fraction, common in simplified crop models, not checked against a tomato-specific reference. |
| `CANOPY_LIGHT_EXTINCTION_COEFF` | 0.75 (added 2026-08-20) | **SOURCED** | Beer-Lambert canopy light-interception coefficient, `1 - exp(-k*LAI)`. High-wire tomato canopies with horizontal leaf orientation are reported at k=0.7-0.9; used 0.75. Drives the transpiration calculation (see `climate-control.md` for the humidity model this feeds). Source: `papers/tomato-canopy-extinction-coefficient.md`. |
| `TRANSPIRATION_ENERGY_FRACTION` | 0.70 (added 2026-08-20) | **SOURCED** | Fraction of canopy-intercepted solar energy converted to latent heat (transpiration) rather than sensible heat. A measured greenhouse tomato study found latent heat flux = 66.4-71.7% of net radiation; used 0.70 (mid). A simplification of the full Stanghellini/Penman-Monteith approach (no dynamic stomatal/VPD feedback) — a fixed fraction. Source: `papers/tomato-transpiration-latent-heat-fraction.md`. |
| `LATENT_HEAT_OF_VAPORIZATION_J_KG` | 2.45e6 (added 2026-08-20) | **ΦΥΣΙΚΗ ΣΤΑΘΕΡΑ / physical constant** | Latent heat of vaporization of water at ~20°C. Standard meteorological value (e.g. FAO-56 Penman-Monteith reference) — not a model assumption. |
| `VPD_MIN_KPA, VPD_OPT_KPA, VPD_MAX_KPA` | 0.2, 0.85, 2.0 (added 2026-08-20) | **SOURCED** | Cardinal points for a bell-shaped VPD response multiplying gross photosynthesis (stomata close under high VPD; gas exchange also suffers near saturation). Literature: optimal range 0.3-1.0 kPa, peak near ~1 kPa, "suitable" VPD <2 kPa, markedly reduced photosynthesis from 1-1.5 kPa. Source: `papers/tomato-vpd-optimal-range.md`. |

## Humidity model (added 2026-08-20)

`twin/climate_model.py` now tracks vapor pressure (kPa) as climate state, alongside temperature and CO2 — the same approach real greenhouse models use, since relative humidity is nonlinear in temperature and awkward to track directly. Two new inputs feed it:

- **Crop transpiration** (`twin/crop_model.py`): computed from solar radiation intercepted by the canopy (via `CANOPY_LIGHT_EXTINCTION_COEFF` and current LAI) times `TRANSPIRATION_ENERGY_FRACTION`, converted to a water mass via the latent heat of vaporization. Zero at night (no light, no canopy interception).
- **Ventilation exchange**: the same air-change rate already computed for the energy balance pulls interior vapor pressure toward outdoor vapor pressure (derived from `weather.py`'s `rh_out_pct`, generated but previously unused) — an exponential decay, structurally identical to how the existing CO2 balance handles ventilation.

**Saturation vapor pressure** uses the Tetens/Magnus formula (`_saturation_vapor_pressure_kpa`), a standard meteorological equation (FAO-56 Penman-Monteith reference, Allen et al. 1998) — not a model assumption, just physics.

## Update 2026-08-20: condensation/dehumidification + VPD feeds photosynthesis

Both gaps noted above (the day this section was first written) are now closed:

- **Passive condensation**: `twin/climate_model.py` now estimates a cover surface temperature (`cover_surface_temp_fraction`) and compares it to the interior air's dew point (`_dew_point_c`) — when the cover is colder, vapor pressure relaxes toward the cover's saturation point (`condensation_rate_constant`), removing moisture even when bulk air is well below 100% RH, matching how real greenhouse condensation works. See `climate-control.md` for the two new (PLACEHOLDER) rate parameters this needs.
- **Active dehumidification**: an idealized setpoint controller (`dehumidification_setpoint_pct`, default 85%) represents the real quote's OptiClima cooling/dehumidification panels — modeled as unconstrained capacity (always reaches the setpoint), since no real capacity spec was available. Tracked as an open gap in `README.md`.
- **VPD now feeds photosynthesis**: `_vpd_response()` multiplies gross assimilation the same way `_temperature_response()` does, using `VPD_MIN_KPA`/`VPD_OPT_KPA`/`VPD_MAX_KPA` (see table above).

## Bug fix: response curves could exceed 1.0 (2026-08-20)

While wiring VPD into photosynthesis, found that `_temperature_response()`'s "normalized product function" (Yin et al. style) only equals exactly 1.0 *at* T_OPT by construction — when T_OPT isn't equidistant from T_MIN/T_MAX (it isn't: T_OPT=27 vs. midpoint 22.5), the raw parabola's true peak sits elsewhere, and the ratio exceeds 1.0 there. It was hitting **~1.15 around 20-25°C** — exactly this greenhouse's normal operating range — meaning photosynthesis had been silently over-boosted this whole time (pre-existing, not something introduced by today's T_OPT change). The new `_vpd_response()` uses the identical shape and has the same flaw (VPD_OPT=0.85 isn't centered between 0.2 and 2.0 either). Both are now clamped at 1.0 (`min(1.0, ...)`). Regression tests added (`test_temperature_response_never_exceeds_one`, `test_vpd_response_never_exceeds_one_and_peaks_at_optimum`).

**Combined effect of the VPD-photosynthesis link + this clamp fix**: baseline 150-day yield moved from 20.96 to **8.43 kg/m²** at the default 85% dehumidification setpoint — a large drop, but not a bug: most daytime hours now sit at VPD well below the 0.85 kPa optimum (median ~0.39 kPa) because 85% RH is a fairly humid ceiling. See the sensitivity table in `climate-control.md`'s `dehumidification_setpoint_pct` row — this is a genuine, adjustable design trade-off now visible for the first time, not something to silently "fix" back to the old yield number.

## Bottom line

The **structure** of the crop model (light/CO2/temperature response curves feeding canopy photosynthesis, minus maintenance respiration, partitioned to fruit by growth stage) is a legitimate simplified version of how real crop models like TOMGRO work. Most of the **numbers** are literature-plausible but not individually calibrated to this greenhouse. Two values (`fruit_partition_fraction_max`, `T_OPT_C`) were found to be conservative relative to the literature and were raised on 2026-08-19 — see the rows above for before/after and the resulting baseline yield change (13.30 → 20.25 kg/m² over a 150-day run).

## Bug fix: nighttime respiration was a no-op (2026-08-20)

Not a numeric assumption — a logic bug in `twin/crop_model.py`. The standing-biomass update used
`new_standing_dm = max(current, current + net_dry_matter_g_m2_hour)`, intended (per its comment)
to prevent biomass from shrinking since senescence/leaf drop isn't modeled. In practice this
clamp discarded **every** hour's net change whenever it was negative — which is every night,
since `gross_assimilation` requires light. Maintenance respiration was therefore silently a no-op
at night, every night, for the whole simulation.

This was found while adding the thermal screen (`climate_control.screen_energy_saving_fraction`):
the screen only acts at night, and its effect on temperature turned out to have **zero** measurable
effect on final yield — traced to this clamp discarding the very hours the screen changes.

Fixed by flooring standing biomass at 0 instead of at its previous value:
`new_standing_dm = max(0.0, current + net_dry_matter_g_m2_hour)`. This lets respiration properly
reduce biomass overnight (real physiology), while still preventing an unphysical negative value.
Senescence/leaf abscission (programmed tissue death) remains genuinely unmodeled — a separate,
still-open gap — but respiration is no longer conflated with it.

Effect: since biomass no longer over-accumulates by skipping nightly respiration, the following
day's respiration cost (which scales with standing biomass) is correspondingly lower, and net
growth available for fruit partitioning is higher. Baseline 150-day yield moved from 20.25 to
**20.96 kg/m²** (fixed respiration alone, screen at its default 0.55 fraction); the thermal
screen's own marginal contribution is small but now non-zero (~20.96 vs ~20.957 kg/m² with the
screen fraction forced to 0 — see `tests/test_crop_model.py` for a unit-level regression check
should this clamp regress).
