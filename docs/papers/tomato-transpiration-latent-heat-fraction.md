# Latent heat partitioning in greenhouse tomato canopies

- **Type:** Web search aggregation, referencing Stanghellini-family transpiration models and a measured greenhouse tomato energy-balance study
- **Retrieved:** 2026-08-20, via web search (this environment cannot fetch full papers directly)
- **Used for:** `TRANSPIRATION_ENERGY_FRACTION` (twin/crop_model.py)

## Data used

> Stanghellini (1987) modified the Penman-Monteith formula for greenhouse crops, incorporating LAI. Research on tomato plants in a greenhouse showed that latent heat flux (λET) was the principal component of net radiation (Rn), accounting for **66.4-71.7%**. The ratio λET/Rn increases linearly as LAI increases.

Used **0.70** (mid of the 66.4-71.7% range) as the fraction of solar radiation intercepted by the canopy (`CANOPY_LIGHT_EXTINCTION_COEFF`) that is converted to latent heat (water vapor via transpiration) rather than sensible heat. This is a simplification of the full Stanghellini/Penman-Monteith approach (which also accounts for stomatal conductance and vapor pressure deficit feedback) — a fixed fraction, not a dynamic stomatal response. Worth revisiting with a proper Stanghellini-style model if transpiration accuracy becomes important (e.g. for irrigation/fertigation scheduling).
