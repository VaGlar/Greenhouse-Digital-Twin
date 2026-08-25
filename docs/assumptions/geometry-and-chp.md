# Geometry & CHP assumptions

`config/greenhouse_example.yaml` → `geometry:` and `chp:` blocks. Model code: `twin/climate_model.py`, `twin/params.py`.

## Geometry

| Parameter | Value | Tag | Notes |
|---|---|---|---|
| `area_m2` | 5000 | **SITE-SPECIFIC** | The stated "5 στρέμματα" design figure. A real vendor quote exists for this greenhouse (`docs/papers/geothermiki-s192g-quote.md`) but its own numbers are internally inconsistent (cover page says 5,280 m²; pricing table says 6,393 m²; stated dimensions 48×100m give 4,800 m²) — kept at 5000 by explicit user decision (2026-08-19), not reconciled against any of the quote's figures. |
| `height_m` | 5.67 (was 5.5, 2026-08-19) | **SOURCED** | Derived from the real quote's arch geometry: 5 bays of 9.6m chord, side height 4.0m, ridge height 6.5m (2.5m rise). Average interior height for a circular-arc roof ≈ side_height + rise×(2/3) ≈ 5.67m. Derivation in `docs/papers/geothermiki-s192g-quote.md`. Coincidentally close to the old placeholder (5.5m). |
| `cover_u_value_w_m2k` | 4.4 (was 6.0, 2026-08-19) | **SOURCED, with caveat** | The real cover material is **double-inflated polyethylene** (not single glass as previously assumed) — 180 micron, 3 layers exterior + 8 layers interior thermal/anti-drip film (`docs/papers/geothermiki-s192g-quote.md`). Double-layer inflated PE with an air gap has a materially lower U-value than single glazing. Used 4.4 W/m²K from [Tunnel Vision Hoops — double-layer inflation systems](https://www.tunnelvisionhoops.com/blog/why-install-a-double-layer-inflation-system-for-your-greenhouse/) (`docs/papers/tunnelvisionhoops-double-layer.md`) — caveat: that source's reference system uses 1mm PE membranes, thicker than this greenhouse's 180-micron film; the air gap (not the plastic) dominates the insulating effect, so treated as a reasonable stand-in, not an exact match. The quote's own "U-value" table (1777.78 W/m²K) is **not usable** — it's the raw conductive resistance of the 180-micron film alone, ignoring the convective air-film resistances that dominate real heat transfer; using it directly would imply an absurdly leaky greenhouse. |
| `cover_transmissivity` | 0.90 (was 0.7, 2026-08-19) | **SOURCED** | 180-micron thermal/anti-drip greenhouse film (matching the real quote's cover spec) is commonly rated 88-92% PAR transmission. Source: `docs/papers/greenhouse-film-180micron-transmission.md` (web search aggregation of product listings, no single canonical citation). |
| `cover_area_factor` | 1.45 (was 1.3, 2026-08-19) | **SOURCED** | Computed from the real quote's geometry (not a generic guess): modeling each bay's roof as a circular arc (9.6m chord, 2.5m rise) gives an arc length ≈11.25m per bay per meter of length (vs. 9.6m flat); total cover area (5 bays' roof arcs × 100m + 2 side walls × 4.0m + 2 end walls at avg height) ÷ floor area (4,800m²) ≈ 1.45. Full derivation in `docs/papers/geothermiki-s192g-quote.md`. |

## CHP

| Parameter | Value | Tag | Notes |
|---|---|---|---|
| `electric_power_kw` | 1000 | **SITE-SPECIFIC** | The stated 1MW CHP design figure. |
| `heat_to_power_ratio` | 1.15 | **PLACEHOLDER, plausible but unverified against this unit** | General CHP literature: reciprocating-engine CHP is typically quoted with a heat:power ratio around 0.8–1.0; some engine-based units with full exhaust + jacket-water heat recovery reach ~1.1–1.2. 1.15 sits at the high end of what was found, not contradicted by it but not confirmed either. Source: [UGI — Combined Heat and Power](https://www.ugi.com/gas-for-business/natural-gas-innovation/combined-heating-power/) and general CHP technology overviews (web articles, no page numbers). **Replace with the actual CHP unit's datasheet value once the equipment is selected** — this ratio matters a lot (it sets how much heat the greenhouse gets "for free"). |
| `co2_kg_per_kwh_elec` | 0.18 | **PLACEHOLDER, derived not sourced** | Not taken from a single reference — back-of-envelope: natural gas combustion emits ≈0.202 kg CO2 per kWh (LHV) of fuel burned (typical EU/UK grid-average gas emission factor); at ~35–40% electrical efficiency, that's ≈2.5 kWh fuel per kWh electrical output, i.e. ≈0.50 kg CO2 combusted per kWh_elec. 0.18 kg/kWh_elec implies roughly a third of total combustion CO2 is captured and dosed to the greenhouse (the rest presumably not recoverable via the flue-gas scrubbing system) — a plausible but unverified assumption. **Should come from the CHP/CO2-dosing system's actual spec once selected**, since flue-gas CO2 recovery fraction varies a lot by scrubber design. |

## Cross-check, 2026-08-25: is the simulated heating demand plausible for this climate?

The user asked whether this greenhouse's heating need should be lower than a Dutch
greenhouse's, even though Dutch greenhouses typically have much better insulation
(double glazing, double energy screens vs. this greenhouse's single-layer double-inflated
PE film). Checked against literature:

> Heating fluctuated between 200 and 600 kWh/m²/y across [northern/central] Europe. [...]
> For Mediterranean plastic greenhouses [...] to maintain day and night temperatures of
> 18/16°C, annual heat energy requirement of PE greenhouses is 95-256 kWh/m².

Source: aggregated from EU greenhouse energy-use review literature (via web search).

This greenhouse's own 330-day simulation (default config) uses 747,236 kWh total heat over
5,000 m² = 149.4 kWh/m²/season, or **≈165 kWh/m²/year** annualized — comfortably inside the
Mediterranean 95-256 kWh/m²/year range, well below the northern-Europe 200-600 kWh/m²/year
floor. Confirms the user's intuition: the climate gap (far fewer heating-degree-days at this
site than in the Netherlands) dominates over the insulation gap (this greenhouse's plainer PE
cover vs. Dutch double-glazing/double-screening) — a Mediterranean greenhouse still ends up
needing meaningfully less heating overall, despite the weaker envelope. The flip side, also
consistent with the same source: Mediterranean greenhouses have a real *cooling* need
(~94 kWh/m²/year for Greece specifically) that Dutch greenhouses largely don't — exactly the
trade-off this greenhouse's CHP (heat) + OptiClima (cooling/dehumidification) combination is
built to cover.

A useful sanity-check that the model's overall heating magnitude isn't wildly off, though not
a substitute for calibrating against this specific greenhouse's own real energy bills once
they exist.

## Physical constants (not assumptions — exact values)

`twin/climate_model.py` also defines two module-level constants that are not modeling choices, just physics:
- `AIR_VOLUMETRIC_HEAT_CAPACITY_J_M3K = 1200` — air density (≈1.2 kg/m³) × specific heat (≈1005 J/kg·K) ≈ 1206 J/m³·K. Standard air property value, any physics/engineering reference.
- `CO2_DENSITY_KG_M3 = 1.83` — density of CO2 gas at ~20°C, standard gas property. Any chemistry/engineering reference (ideal gas law at 1 atm, 293K, molar mass 44 g/mol).

These don't need recalibration — they're physical facts, not greenhouse-specific assumptions.
