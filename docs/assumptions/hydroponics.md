# Hydroponics assumptions

`config/greenhouse_example.yaml` → `hydroponic:` block (`twin/params.py`'s `HydroponicParams`).
Implemented in three planned levels (agreed with the user 2026-08-26) — Level A and Level B (plus
the damped N/K/Mg/B tier and the informational P/S/Fe/Mn/Zn/Cu/Mo tier) are all implemented as of
2026-08-28. Level D (ML recalibration) remains a future idea only, not started.

## System-type correction (2026-08-26)

`hydroponic.system_type` was `"NFT"` (Nutrient Film Technique) — a placeholder flag from v1 that
was never checked against real practice. NFT is standard for leafy greens/lettuce, not
indeterminate high-wire tomato: real commercial tomato greenhouses (and this project's own
Northern Greece precedent, Θερμοκήπια Σαββίδη / Dramello Fresh, plus this project's own vendor
quote's Spagnol BravoJet EC/pH fertigation equipment — see
`docs/papers/tomato-variety-selection-northern-greece.md` and
`docs/papers/geothermiki-s192g-quote.md`) use **drip-irrigated substrate** (rockwool or coco
slabs). Corrected to `"drip_substrate"`, with a new `substrate_type: "rockwool"` field
(descriptive only — doesn't yet feed the physics; coco is the other common choice).

## Level A: physical fertigation consumption

The three previous "physical, not yet priced" electricity systems (dehumidification,
ventilation, recirculation fans — see `economics.md`) get a fourth: the fertigation dosing pump.
Unlike those three, this one also tracks water and fertilizer mass, not just electricity.

| Parameter | Value | Tag | Notes |
|---|---|---|---|
| `ec_target_ms_cm` | 3.0 | **SOURCED** | 2.0-3.5 mS/cm is the commonly cited target range for greenhouse tomato nutrient solution. Was already shown (2.5-3.5) as a purely informational reference value in the frontend's "Συνταγή γεωπονίας" tab before this work — now a real `HydroponicParams` field the physics actually reads. Source: `docs/papers/hydroponic-fertigation-level-a.md`. |
| `ph_target` | 6.0 | **SOURCED** | 5.5-6.5 is the standard nutrient-availability optimum (outside this range, specific nutrients become chemically unavailable to the plant even if present in solution). Not yet wired into any model behavior — pH's effect is much more a hard availability threshold than a continuous dial, and no PH-driven yield/quality mechanism has been added (candidate for Level B/C). Source: same as above. |
| `drainage_target_fraction` | 0.25 | **SOURCED** | 20-30% leaching fraction is standard substrate-culture practice — irrigating somewhat beyond what the plant will actually use, so the excess flushes accumulated salts out of the root zone rather than letting them concentrate over time. Source: same as above. |
| `irrigation_pump_specific_power_kwh_per_m3` | 0.28 | **SOURCED (general average, not this specific pump)** | A global study on irrigation energy footprints finds drip irrigation averages ~1.0 MJ/m³ (≈0.28 kWh/m³), noticeably lower than sprinkler (1.8 MJ/m³) thanks to drip's lower operating pressure. This is a general drip-irrigation figure across agriculture broadly (includes water sourcing/conveyance in some of the underlying data), not a spec for this greenhouse's actual Spagnol BravoJet pump — flagged as an approximation, not a real product spec. Source: `docs/papers/hydroponic-fertigation-level-a.md`. |
| `fertilizer_g_per_l_per_ec_unit` | 0.64 | **PLACEHOLDER** | Generic EC-to-TDS conversion factor (EC in mS/cm × ~640 ≈ TDS in ppm/mg per liter, using the commonly-cited "0.64 scale" — other conventions use 0.5 or 0.7). This converts EC into an approximate fertilizer *mass* dosed, but real dosing depends on the specific fertilizer blend's composition, which isn't available for the real BravoJet system's actual fertilizer choice. Treat `total_fertilizer_dosed_kg` as an order-of-magnitude estimate, not a real quote-able mass. |

### Derivation (not new crop-model physics — a reporting/derivation layer, same pattern as the electricity fields in `economics.md`)

Irrigation volume is tied to the crop model's own transpiration output (`twin/crop_model.py`'s
`transpiration_kg_m2_hour`, already computed every hour for the humidity balance) plus the
leaching fraction above — matching how a real drip-substrate system is actually scheduled (dose
somewhat beyond what the plant will use, on purpose):

```
irrigation_water_kg_per_hour = transpiration_kg_per_hour / (1 - drainage_target_fraction)
drainage_water_kg_per_hour   = irrigation_water_kg_per_hour - transpiration_kg_per_hour
fertigation_elec_kw          = (irrigation_water_kg_per_hour / 1000) * irrigation_pump_specific_power_kwh_per_m3
fertilizer_dosed_g_per_hour  = irrigation_water_kg_per_hour * ec_target_ms_cm * fertilizer_g_per_l_per_ec_unit
```

(Water density ~1000 kg/m³, so kg and liters are interchangeable here.) Aggregated in
`api/main.py` the same way as the electricity fields: `irrigation_water_l_day` /
`drainage_water_l_day` / `fertilizer_dosed_g_day` are daily *totals* (a grower thinks in
liters/kg per day, not an average hourly rate); `fertigation_elec_kw` is a daily *mean rate*
like the other electricity fields, so it stays comparable to them on the same chart.
`total_fertigation_elec_kwh` is folded into `summary.total_electricity_kwh` alongside
dehumidification/ventilation/recirculation.

**Known simplification**: irrigation is purely demand-following (zero at night, since
transpiration is zero with no light) — no baseline/maintenance irrigation shot is modeled for
substrate moisture upkeep between light hours, which some real systems do run. Consistent with
how this model already treats ventilation/dehumidification as need-based rather than
scheduled.

## Level B and beyond — implemented 2026-08-28

Planned in detail 2026-08-26 (see git history for the original design-only version of this
section), implemented 2026-08-28 together with the damped N/K/Mg/B tier and the informational
P/S/Fe/Mn/Zn/Cu/Mo tier, in one pass (user's choice — all three tiers together rather than Level B
alone). All derivation lives in `api/main.py`'s `/simulate` handler, calling small pure methods
on `HydroponicParams` (`twin/params.py`): `effective_dry_matter_content_fruit`,
`ber_yield_loss_fraction`, `recipe_adequacy_multiplier`. The crop model's hourly loop
(`twin/crop_model.py`) is untouched — EC/recipe are static config values for the whole run in this
design, so these are all post-hoc scalar adjustments to `final_yield_kg_m2`, not new hourly
physics. Covered by `tests/test_params.py` (the per-mechanism formulas) and `tests/test_api.py`
(the `/simulate` summary fields end to end).

### Level B: EC → fruit weight and BER (Blossom End Rot) risk — full rigor, real effect

Two mechanisms, both applied as a **post-hoc derivation layer in `api/main.py`** (not inside
`twin/crop_model.py`'s hourly loop) — EC is a single static config value for the whole run in
this design (no time-varying EC schedule modeled), so a per-hour physics change isn't needed; a
scalar adjustment to the reported yield is mathematically equivalent and much lower-risk (doesn't
touch the hourly loop or any of the 91 existing tests).

**B1. EC → fruit dry-matter fraction (denser/smaller fruit at higher EC).** A study comparing
low EC (2.3 dS/m) vs. high EC (5.0 dS/m) hydroponic tomato found fruit dry matter content
increased by 0.5-1 percentage points over that range — i.e. ~0.19-0.37 points per +1 mS/cm, higher
EC producing more "concentrated"/smaller fresh fruit for the same partitioned dry matter (real,
well-documented osmotic-stress-on-fruit-quality trade-off). Source: [MDPI — The Effect of
Electrical Conductivity on Fruit Growth Pattern in Hydroponically Grown Tomatoes](https://www.mdpi.com/2673-7655/2/3/23)
and related EC/quality studies found via web search 2026-08-26 (search query: "tomato fruit dry
matter content percentage increase with nutrient solution EC hydroponic").

**Implemented** (`HydroponicParams`): `ec_dry_matter_reference_ms_cm = 2.3` (the study's low-EC
baseline, SOURCED), `ec_dry_matter_slope_per_ms_cm = 0.0028` (fraction per +1 mS/cm, i.e. ~0.28
percentage points, SOURCED — midpoint of the 0.19-0.37 range). Derivation: since
`dry_matter_content_fruit` is a constant divisor throughout the whole run in the current model
(`fresh_weight = dry_matter / dry_matter_content_fruit`), dividing the *whole* cumulative/final
yield by the ratio `effective_dry_matter_content_fruit = 1 + ec_dry_matter_slope_per_ms_cm *
(ec_target_ms_cm - ec_dry_matter_reference_ms_cm)` (a `HydroponicParams` property — the constant
`dry_matter_content_fruit` itself cancels out of the ratio, so it isn't referenced directly) is
exactly equivalent to having used the EC-adjusted fraction from hour 1 — no hourly-loop change
needed. At the default `ec_target_ms_cm = 3.0`, this is a small effect (~0.2% below the base
model's reported yield).

**B2. EC/salinity → BER risk → marketable yield loss.** A study found the critical salinity
threshold for a significant BER incidence increase is 3-4 dS/m, and marketable yield losses of
8.9-33.8% (varying by year/severity) once past it. Source: [PMC — The Effects of Saline Water
Drip Irrigation on Tomato Yield, Quality, and Blossom-End Rot Incidence](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4634986/)
(search query: "blossom end rot tomato risk calcium high EC irrigation quantified percentage").
Mechanism: high EC/salinity impairs calcium uptake (Ca is transported solely via the
transpiration stream, so anything restricting water/Ca flow to the fruit — high EC, irregular
irrigation, high humidity slowing transpiration — increases BER risk).

**Implemented**: `ec_ber_threshold_ms_cm = 3.5` (SOURCED, midpoint of the 3-4 dS/m range),
`ber_yield_loss_fraction_per_ms_cm_above_threshold = 0.10` (SOURCED mechanism, PLACEHOLDER slope —
a judgment call within the cited 8.9-33.8% range, chosen by the user 2026-08-28 as the doc's own
suggested default: a linear ramp reaching ~20% loss by threshold+2 mS/cm), capped at
`ber_yield_loss_fraction_max = 0.35`. Formula (`HydroponicParams.ber_yield_loss_fraction`):
`clamp(0, max_loss, slope * max(0, ec_target_ms_cm - ec_ber_threshold_ms_cm))`. At the default
`ec_target_ms_cm = 3.0` (below the 3.5 threshold), loss is exactly 0 — doesn't disturb the current
default-config run.

New summary outputs (`api/main.py` `/simulate`): `ec_adjusted_final_yield_kg_m2` (after B1),
`ber_yield_loss_fraction`, `recipe_adequacy_multiplier` (see damped tier below),
`marketable_yield_kg_m2` (after B1, B2, and the damped tier combined), `total_marketable_yield_kg`.
The existing `daily_series.fruit_fresh_yield_kg_m2` chart stays as the base biomass-model curve,
unadjusted — only the summary-level scalars carry the EC/BER/recipe adjustment, keeping the
footprint small. Surfaced in the frontend's "Συνταγή γεωπονίας" tab results panel.

### Recipe "damped" tier: N, K, Mg, B — real mechanism, deliberately small/capped magnitude

Explicit user framing (2026-08-26): unlike Level B above (which should be as rigorously
calibrated as the literature allows), these four get a **real, non-zero mechanism** but a
**deliberately conservative, capped magnitude** given much higher uncertainty in isolating a
single nutrient's effect in a simplified model — with an explicitly logged future path (see
"Level D" below) to recalibrate for real once actual sensor/yield data exists.

Design pattern for all four (`HydroponicParams._nutrient_penalty`, `.recipe_adequacy_multiplier`):
a **sufficiency range** `[min_optimal_ppm, max_optimal_ppm]` per nutrient — a target inside the
range costs nothing; outside it, a linear penalty ramping from 0 at the boundary to
`damped_nutrient_penalty_cap_fraction = 0.02` (PLACEHOLDER, 2% cap) once the ppm value is a full
range-width beyond that boundary, capped there. The four individual `(1 - penalty)` factors are
combined multiplicatively into `recipe_adequacy_multiplier`, itself floored at
`recipe_adequacy_multiplier_min = 0.85` (PLACEHOLDER) so the whole tier can never produce an
unrealistically large swing regardless of how far out of range several nutrients are at once —
though at the 2% individual cap, four simultaneous worst-case nutrients only reach ~7.8% combined
reduction in practice, well short of that floor. All four ppm targets and sufficiency ranges are
**SOURCED** to real published tomato hydroponic formulas; the penalty slope/caps are explicitly
**PLACEHOLDER** (the mechanism is real, the magnitude is a deliberate guess).

Reference concentrations (SOURCED, University of Arizona CEAC / University of Florida IFAS
extension formulas for hydroponic tomato; CEAC values below reconfirmed 2026-08-28 via a direct
recheck of the CEAC PDF, since the original 2026-08-26 pass couldn't fetch it and left Mg/S/Zn as
unconfirmed placeholders. Sources: [CEAC Arizona tomato formula PDF](https://www.ceac.arizona.edu/sites/default/files/Tomato%20formula.pdf),
[Florida EDIS HS796/CV216](https://journals.flvc.org/edis/article/view/136205/version/72729/140739)):

| Nutrient | Typical range (ppm) | Config default | Mechanism if outside range |
|---|---|---|---|
| N | ~60-150 (Florida: 60-70 early season → 150-200 late season; Arizona fruiting stage 144) | `n_ppm = 105` (mid-range) | Excess N shifts partitioning toward vegetative growth at fruit's expense — one cited study found up to 32.9% fruit-yield swing between low/high-N regimes (real magnitude; our damped version uses much less, capped at 2%). Source: [T&F — Reduced nitrogen proportion during vegetative stage](https://www.tandfonline.com/doi/full/10.1080/09064710.2022.2060855). |
| K | ~199-400 (Arizona 199, Florida late-season 300-400) | `k_ppm = 300` | Low K reduces fruit firmness/quality (TSS, color) — no clean tomato-specific yield percentage found; treated as a small marketable-fraction penalty, not a fresh-weight change (distinct channel from B1/EC). Source: [Springer — Tomato Fruit Yield, Quality, and Nutrient Status in Response to K:Ca Balance and EC](https://link.springer.com/article/10.1007/s42729-019-00133-9). Note: excess K can itself induce Ca/Mg deficiency (nutrient antagonism) — not modeled, just documented. |
| Mg | 45-70 (CEAC Arizona formula confirms **65 ppm**, constant across all 3 of its recipe variants — recheck 2026-08-28 corrects the original 2026-08-26 pass's unconfirmed ~50 guess) | `mg_ppm = 65` | Deficiency → chlorosis → reduced photosynthesis (real, well-documented mechanism structurally identical to the model's existing temperature/VPD response curves) but no tomato-specific quantified percentage was found — magnitude is a placeholder guess, more so than the other three. Source: [ScienceDirect — Effects on photosynthesis and energy balance in tomato leaves under Mg deficiency](https://www.sciencedirect.com/science/article/abs/pii/S0981942825001998) — abstract confirms mechanism, not a specific percentage. |
| B | 0.30-0.50 (CEAC Arizona micronutrient formula: 0.40 ppm) | `b_ppm = 0.40` | Deficiency → reduced pollen viability/fruit set — same structural slot as the model's existing `_fruit_set_temp_response` (a second multiplicative factor, not a new mechanism type). No tomato-specific percentage found; qualitative mechanism only. Source: [Yara — Role of Boron in Tomato Production](https://www.yara.us/crop-nutrition/tomato/role-of-boron/). |

### Recipe "informational" tier: P, S, Fe, Mn, Zn, Cu, Mo — no model effect, real reference values

Same treatment as the existing "Επικονίαση" (pollination) block in the frontend recipe tab —
displayed for reference, explicitly **not** read by any physics. Reference concentrations
(SOURCED, CEAC Arizona formula, rechecked 2026-08-28): `p_ppm = 62`, `s_ppm = 110` (CEAC's 3
recipe variants range ~102-121 ppm, midpoint used — corrects the original pass's unconfirmed
65-113 guess), `fe_ppm = 2.5`, `mn_ppm = 0.55`, `zn_ppm = 0.33`, `cu_ppm = 0.05`, `mo_ppm = 0.05`.
**Mn and Zn have a notable cross-source disagreement**: Florida IFAS cites Mn ≈ 0.62 ppm (vs.
CEAC's 0.55) and, more significantly, Zn ≈ 0.09 ppm — a 3.6× difference from CEAC's 0.33 ppm.
CEAC was used throughout since it's one internally-consistent formula (all values from the same
document), rather than mixing sources per-element, but this discrepancy is worth resolving against
a real fertilizer blend spec once one exists (same caveat as `fertilizer_g_per_l_per_ec_unit` in
Level A above). Ca is *not* in this informational-only list — it already gets real model treatment
via BER risk (B2 above).

### Level D (future, not this pass): ML-based recalibration

User's own framing (2026-08-26): once the real greenhouse exists and has actual sensor/yield data
across multiple seasons and EC/recipe conditions, a machine-learning mechanism could replace or
recalibrate the placeholder coefficients above (especially the damped-tier slopes/caps, which are
the least confidently sourced) with a real fitted correlation. **Not started, not scaffolded** —
this needs real data that doesn't exist yet (the greenhouse isn't built), and building any
ML/training infrastructure now would be premature complexity ahead of having anything to train on.
Logged here so the idea isn't lost, not as an active work item.
