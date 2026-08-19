# Determining greenhouse heat loss

- **Publisher:** Greenhouse Management (trade publication)
- **URL:** https://www.greenhousemag.com/article/technology-determining-greenhouse-heat-loss/
- **Type:** Web article (not paginated)
- **Retrieved:** 2026-08-19, via web search (this environment cannot fetch page content directly)
- **Used for:** `geometry.cover_u_value_w_m2k` (config/greenhouse_example.yaml)

## Excerpt used

> Typical U-value for greenhouses with a single layer of glass is 1.15 (Btu/hr·sq ft·°F).

Converted to SI: 1.15 Btu/hr·ft²·°F × 5.678 = **≈6.53 W/m²K**, which is the greenhouse-relevant figure (windier exterior film coefficient than a calm-air building-window U-value, which reads much lower, ~2.7–3.8 W/m²K for single glazing). The config's `cover_u_value_w_m2k: 6.0` is consistent with this.
