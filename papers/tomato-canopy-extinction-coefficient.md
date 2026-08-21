# Canopy light extinction coefficient (Beer-Lambert), high-wire tomato

- **Type:** Web search aggregation of canopy light-interception literature (general Beer-Lambert extinction coefficient references plus tomato-specific figures)
- **Retrieved:** 2026-08-20, via web search
- **Used for:** `CANOPY_LIGHT_EXTINCTION_COEFF` (twin/crop_model.py)

## Data used

> Typical values for k (Beer-Lambert extinction coefficient) are in the range of 0.5 to 0.9 across crop canopies generally. For tomatoes specifically, the extinction coefficient is typically 0.7 to 0.9 for high-wire tomatoes with horizontal leaf orientation.

Used **0.75** (toward the low end of the tomato-specific 0.7-0.9 range) for the fraction of solar radiation intercepted by the canopy as a function of LAI: `1 - exp(-k * LAI)`. Drives the transpiration calculation in `twin/crop_model.py`.
