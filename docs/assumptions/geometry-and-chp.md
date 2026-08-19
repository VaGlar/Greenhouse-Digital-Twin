# Geometry & CHP assumptions

`config/greenhouse_example.yaml` → `geometry:` and `chp:` blocks. Model code: `twin/climate_model.py`, `twin/params.py`.

## Geometry

| Parameter | Value | Tag | Notes |
|---|---|---|---|
| `area_m2` | 5000 | **SITE-SPECIFIC** | The stated "5 στρέμματα" design figure. Confirm against final survey. |
| `height_m` | 5.5 | **PLACEHOLDER** | Typical gutter/ridge height order-of-magnitude for a modern Venlo-type greenhouse. Not individually sourced — replace with the actual structural drawing figure. |
| `cover_u_value_w_m2k` | 6.0 | **SOURCED** | Greenhouse-specific single-glass U-value (as distinct from a *building window* U-value, which is measured in calm indoor/outdoor air and reads much lower, ~2.7–3.8 W/m²K). Greenhouse literature quotes **1.15 Btu/hr·ft²·°F** for single-layer glass under the windier, greenhouse-relevant film coefficients — converts to **≈6.53 W/m²K** (1 Btu/hr·ft²·°F = 5.678 W/m²K), consistent with the config's 6.0. Source: [Greenhouse Management — "Determining greenhouse heat loss"](https://www.greenhousemag.com/article/technology-determining-greenhouse-heat-loss/) (web article, no page number — trade publication, not paginated). |
| `cover_transmissivity` | 0.7 | **PLACEHOLDER** | Commonly cited textbook range for single-glass greenhouse cover is roughly 70–90% depending on glass type/age/dirt accumulation. 0.7 is the conservative end. Not individually verified against a specific source — worth revisiting once the actual glazing spec (glass type, coating) is known. |
| `cover_area_factor` | 1.3 | **PLACEHOLDER** | Geometric approximation (roof + wall surface area as a multiple of floor area) — depends on the real building's height/span/shape, not a literature figure. Should be computed directly from the real structural geometry once available, not left as a flat multiplier. |

## CHP

| Parameter | Value | Tag | Notes |
|---|---|---|---|
| `electric_power_kw` | 1000 | **SITE-SPECIFIC** | The stated 1MW CHP design figure. |
| `heat_to_power_ratio` | 1.15 | **PLACEHOLDER, plausible but unverified against this unit** | General CHP literature: reciprocating-engine CHP is typically quoted with a heat:power ratio around 0.8–1.0; some engine-based units with full exhaust + jacket-water heat recovery reach ~1.1–1.2. 1.15 sits at the high end of what was found, not contradicted by it but not confirmed either. Source: [UGI — Combined Heat and Power](https://www.ugi.com/gas-for-business/natural-gas-innovation/combined-heating-power/) and general CHP technology overviews (web articles, no page numbers). **Replace with the actual CHP unit's datasheet value once the equipment is selected** — this ratio matters a lot (it sets how much heat the greenhouse gets "for free"). |
| `co2_kg_per_kwh_elec` | 0.18 | **PLACEHOLDER, derived not sourced** | Not taken from a single reference — back-of-envelope: natural gas combustion emits ≈0.202 kg CO2 per kWh (LHV) of fuel burned (typical EU/UK grid-average gas emission factor); at ~35–40% electrical efficiency, that's ≈2.5 kWh fuel per kWh electrical output, i.e. ≈0.50 kg CO2 combusted per kWh_elec. 0.18 kg/kWh_elec implies roughly a third of total combustion CO2 is captured and dosed to the greenhouse (the rest presumably not recoverable via the flue-gas scrubbing system) — a plausible but unverified assumption. **Should come from the CHP/CO2-dosing system's actual spec once selected**, since flue-gas CO2 recovery fraction varies a lot by scrubber design. |

## Physical constants (not assumptions — exact values)

`twin/climate_model.py` also defines two module-level constants that are not modeling choices, just physics:
- `AIR_VOLUMETRIC_HEAT_CAPACITY_J_M3K = 1200` — air density (≈1.2 kg/m³) × specific heat (≈1005 J/kg·K) ≈ 1206 J/m³·K. Standard air property value, any physics/engineering reference.
- `CO2_DENSITY_KG_M3 = 1.83` — density of CO2 gas at ~20°C, standard gas property. Any chemistry/engineering reference (ideal gas law at 1 atm, 293K, molar mass 44 g/mol).

These don't need recalibration — they're physical facts, not greenhouse-specific assumptions.
