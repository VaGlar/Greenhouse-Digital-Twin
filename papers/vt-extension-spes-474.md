# Protective Agriculture Production Series: Plant density recommendations

- **Publisher:** Virginia Cooperative Extension (Virginia Tech), publication SPES-474
- **URL:** https://www.pubs.ext.vt.edu/SPES/spes-474/spes-474.html
- **Type:** University extension publication (web page, not paginated in the fetched form — check the PDF version on the VT Extension site for a print page reference if needed)
- **Retrieved:** 2026-08-19, via web search
- **Used for:** `crop.density_plants_per_m2`, `crop.reference_density_plants_per_m2` (config/greenhouse_example.yaml, twin/params.py)

## Excerpt used

> Greenhouse tomato grown to a single stem sits at 2.3 to 2.5 plants/m² (0.21 to 0.23 per ft²), often pushed to 3 to 3.5 stems/m² by keeping a second head... An initial planting density target of 2.3 plants/m² is reasonable for most beefsteak and cluster tomato cultivars in commercial high-wire greenhouse production.

This directly matches the config's `density_plants_per_m2: 2.5` (single-stem, beefsteak variety) and was the basis for setting `reference_density_plants_per_m2: 2.5` — the density at which the crop model's canopy is treated as fully closed.
