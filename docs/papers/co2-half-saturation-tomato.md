# CO2 half-saturation constant for tomato photosynthesis — Ci vs Ca

- **Type:** Web search aggregation, general C3/tomato photosynthesis CO2-response (FvCB model) literature — no single paper gives a clean, directly-usable Ca-based (ambient CO2) half-saturation ppm value
- **Retrieved:** 2026-08-20, via web search
- **Used for:** `CO2_HALF_SAT_PPM` (twin/crop_model.py)

## What was found

> A/Ci (assimilation vs. intercellular CO2) curves for tomato are typically measured at 25°C. The Michaelis-Menten constants for RuBP carboxylation (KmC) in FvCB-model literature are commonly cited in the ~270-300 µbar (~ppm) range at 25°C for C3 species generally, tomato included.

This is a **Ci-based** constant (intercellular CO2 concentration inside the leaf), not directly usable in our model, which drives its CO2 response off greenhouse air CO2 (Ca — what a CO2 sensor/dosing controller actually measures and controls). Well-watered C3 plants typically run a Ci/Ca ratio of roughly 0.7-0.8 (stomatal + mesophyll conductance creates a drawdown from ambient to intercellular CO2).

## Conversion used

Ca-equivalent half-saturation ≈ Ci-based Km / (Ci/Ca ratio) ≈ 285 / 0.75 ≈ 380 ppm, in the same ballpark as simply dividing the 270-300 range by 0.7-0.8 (giving ~340-430 ppm). Used the midpoint of that derived range, **375 ppm**, raised from an unsourced 200.

## Important limitation (not resolved by this number)

No value of this constant can make the model's rectangular-hyperbola CO2 response reproduce the ~56-74% season-long yield gain reported from 500→700 ppm CO2 enrichment (see `papers/tomato-co2-optimum-700ppm.md`) — a rectangular hyperbola's elasticity is always below 1, so the model's % output gain is structurally capped below the % input gain (+40% CO2, 500→700). Real large CO2-enrichment yield gains come from season-long compounding effects (leaf area growth, reduced water stress) that this instantaneous per-hour multiplicative factor cannot represent. See `docs/assumptions/crop-model.md` and `docs/assumptions/README.md`'s open-gaps list.
