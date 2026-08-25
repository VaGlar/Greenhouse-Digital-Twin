# 180 Micron Premium Greenhouse Film — light transmission

- **Type:** Web search aggregation of greenhouse film product specifications (multiple retailer/manufacturer listings for 180-micron greenhouse film)
- **Retrieved:** 2026-08-19, via web search (this environment cannot fetch product pages directly; no single canonical URL — figures corroborated across several 180-micron greenhouse film product listings found in search)
- **Used for:** `geometry.cover_transmissivity` (config/greenhouse_example.yaml)

## Data used

> 180µm Premium Greenhouse Film offers 90% light transmission, specifically 88-92% PAR (photosynthetically active radiation) transmission. Advanced internal coating prevents condensation droplets (anti-drip). Reduces heat loss by 15-25% compared to standard films.

Matches the real quote's cover spec (`papers/geothermiki-s192g-quote.md`): 180-micron thermal + anti-drip double-inflated PE film. Used 0.90 (mid of the 88-92% range) for `cover_transmissivity`, up from the earlier single-glass-based placeholder of 0.7.
