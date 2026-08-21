# Exploring adequate CO2 elevation for optimum tomato growth and yield under protected cultivation

- **Type:** Journal article (tested ambient 500 ppm + elevated 700/850/1000 ppm CO2 on tomato under protected cultivation, two growing seasons)
- **URLs:** [PubMed](https://pubmed.ncbi.nlm.nih.gov/37742534/) · [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0176161723001876) · [ResearchGate](https://www.researchgate.net/publication/373959933_Exploring_adequate_CO2_elevation_for_optimum_tomato_growth_and_yield_under_protected_cultivation)
- **Retrieved:** 2026-08-20, via web search (abstract/summary — full text not fetchable from this environment)
- **Used for:** `CO2_SATURATION_PPM` (twin/crop_model.py), `climate_control.co2_setpoint_day_ppm` (config/greenhouse_example.yaml)

## Data used

> 700 ppm was the optimal CO2 concentration for improving tomato yield, fruit quality, and water use efficiency. The optimum yield was increased under 700 µmol mol⁻¹ by 73.95% and 55.58% in autumn-winter 2020 and spring-summer 2021, respectively, versus ambient (500 ppm). Super-elevated CO2 (850, 1000 ppm) did not positively influence the tomato growth process and yield under adequate water and fertilizer conditions.

## Why this mattered

The model's `_co2_response()` was a plain Michaelis-Menten curve (`co2/(co2+K)`) with no ceiling — it rises asymptotically toward 1 forever, so raising the CO2 setpoint kept increasing simulated yield with no limit, contradicting this study's finding that yield gains stop at 700 ppm. The user noticed this directly ("however much I raise it, yield keeps rising — 1200ppm should be toxic, this isn't right") on 2026-08-20.

**Fix**: clamp the response function's input at `CO2_SATURATION_PPM = 700.0` — the curve still rises the same way up to 700 ppm, then stays flat above it, rather than fabricating a decline this specific study doesn't clearly establish (it says "did not positively influence," not "reduced" — a plateau, not a proven toxic decline, is the defensible read). `config/greenhouse_example.yaml`'s `co2_setpoint_day_ppm` was also corrected from 900 to 700 to match, since 900 was spending CO2 dosing capacity for zero additional yield.

**Not addressed in this pass** (per user's "wait" — holding off pending further discussion): whether other model constants (`P_MAX_UMOL_M2_LEAF_S`, `CO2_HALF_SAT_PPM`, etc.) should be jointly recalibrated now that this ceiling exists.
