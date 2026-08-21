# CO2 enrichment increases tomato leaf area index (LAI) growth, not just instantaneous photosynthesis

- **Type:** Web search aggregation, tomato CO2-enrichment growth-parameter studies (same family as `papers/tomato-co2-optimum-700ppm.md` — dose-response testing 500/700/850/1000 ppm)
- **Retrieved:** 2026-08-20, via web search
- **Used for:** `CO2_LAI_BOOST_MAX`, `CO2_AMBIENT_REFERENCE_PPM` (twin/crop_model.py)

## Data used

> Plant height, stem diameter and LAI were enhanced compared to ambient CO2 at the optimum level under 1000 µmol mol⁻¹ (by 50.53%, 20.98%, 44.44%) and 700 µmol mol⁻¹ (by 22.41%, 12.09%, **26.88%**) in different growing seasons. Significant improvement in growth-indicating parameters like leaf area, LAI, leaf area duration and crop growth rate were measured at elevated CO2 levels at different stages of crop growth. Local application of CO2 increased the projected leaf area and thus cumulative light interception.

## Why this mattered

The user pointed out that raising the CO2 setpoint kept increasing yield with no limit (fixed via `CO2_SATURATION_PPM`, see `papers/tomato-co2-optimum-700ppm.md`), then asked whether `CO2_HALF_SAT_PPM` needed recalibrating so the model's ambient→700ppm yield sensitivity would better match the ~56-74% season-long gain the same study family reports. Math showed no value of `CO2_HALF_SAT_PPM` alone can do this — a rectangular hyperbola's elasticity is always below 1, so the model's % output gain is structurally capped below the % input gain (+40% CO2, 420→700ppm), no matter the half-saturation constant.

The missing piece: real CO2-enrichment yield gains come mostly from **more/bigger leaves** (LAI), which compounds over the season (more canopy → more total assimilation every subsequent hour) — not just a faster instantaneous photosynthesis rate. `twin/crop_model.py`'s `_lai()` now scales its `effective_lai_max` by a CO2-driven factor: `1.0` at `CO2_AMBIENT_REFERENCE_PPM` (420 ppm), rising to `1.0 + CO2_LAI_BOOST_MAX` (`1.2688`) at `CO2_SATURATION_PPM` (700 ppm), reusing the same saturating shape as `_co2_response` in between for consistency.

## Result

Combined with the biochemically-sourced `CO2_HALF_SAT_PPM = 375` (see `papers/co2-half-saturation-tomato.md`), a sensitivity sweep across K = 100..600 showed K=375 lands the model's ambient(420)→700ppm yield gain at **~56.4%**, right at the low end of the 56-74% reported range — confirmed with the user before locking in this value. Baseline 150-day yield at the default 700ppm setpoint: **15.64 kg/m²** (was 12.33 with the instantaneous-only fix, 20.96 before any CO2 corrections this session).
