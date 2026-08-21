# Greenhouse cover condensation and dew point physics

- **Type:** Web search aggregation (general meteorological/greenhouse-engineering condensation references)
- **Retrieved:** 2026-08-20, via web search
- **Used for:** the condensation mechanism in `twin/climate_model.py` (`cover_surface_temp_fraction`, `condensation_rate_constant`, `_dew_point_c`)

## Data used

> Condensation on plants/covers occurs when leaf/cover surface temperature is below the dew point of the air. As air cools to the dew point at night, condensation occurs on cooler surfaces such as leaves and glazing. The amount of humidity removed depends on the difference between the absolute humidity of the air and the absolute humidity at the dew point. Dehumidifying systems work by maintaining a surface temperature above the dew point.

This confirms the qualitative physics used (condensation happens whenever a surface is below the air's dew point, not only when bulk air hits 100% RH) but the search did not yield a specific, citable value for how quickly a greenhouse cover's surface temperature tracks between indoor/outdoor air, or a real condensation mass-transfer rate constant. `cover_surface_temp_fraction` (0.3) and `condensation_rate_constant` (2.0/hour) in `twin/climate_model.py` are therefore **engineering approximations** (PLACEHOLDER), not individually sourced numbers — only the underlying mechanism (dew point vs. surface temperature) is sourced. See `docs/assumptions/climate-control.md`.
