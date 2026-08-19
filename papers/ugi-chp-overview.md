# Combined Heat and Power (CHP) — UGI overview

- **Publisher:** UGI (US gas utility, business/industry overview page)
- **URL:** https://www.ugi.com/gas-for-business/natural-gas-innovation/combined-heating-power/
- **Type:** Web article (not paginated)
- **Retrieved:** 2026-08-19, via web search
- **Used for:** `chp.heat_to_power_ratio` (config/greenhouse_example.yaml)

## Excerpt used

> CHP systems typically achieve effective electrical efficiencies of 50% to 70% by recovering waste heat... Engine-based CHP solutions are ideal for industrial customers with power-to-heat ratio higher than 0.8, while turbine-based solutions are preferred for industrial users with power-to-heat ratios lower than 0.8.

General industry consensus (from this and related overview pages found in the same search): reciprocating-engine CHP typically runs a heat:power ratio around **0.8–1.0**, with some engine units reaching **~1.1–1.2** when both jacket-water and exhaust heat are fully recovered. The config's `heat_to_power_ratio: 1.15` sits at the high end of this range — plausible but not confirmed against a specific unit's datasheet. See `docs/assumptions/geometry-and-chp.md` for the recommendation to replace this with the actual selected CHP unit's spec.
