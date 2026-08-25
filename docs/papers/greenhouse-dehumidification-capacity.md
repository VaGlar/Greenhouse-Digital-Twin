# Greenhouse active dehumidification: real-world removal capacity

- **Type:** Web search aggregation (commercial product specs + a semi-closed greenhouse measurement)
- **Retrieved:** 2026-08-25, via web search
- **Used for:** `twin/params.py` (`ClimateControlParams.dehumidification_capacity_kg_water_per_hour`)

## Data used

The real vendor quote for this greenhouse (`geothermiki-s192g-quote.md`) mentions the OptiClima
system includes "cooling panels, dehumidification" but gives no capacity spec (no kg-water/hour
figure, no unit count). Absent that, this parameter is grounded in comparable real systems, not
the specific (not-yet-installed) unit:

> The DG-12 dehumidifier condenses up to 48 liters of water per hour.

Source: DryGair commercial greenhouse dehumidifier product listing, via [royalbrinkman.com](https://royalbrinkman.com/promotion/featured-products/drygair).

> A cooling system in a semi-closed greenhouse removed about 75 kg/h of water from the air when operating with specific parameters.

Source: aggregated from search results referencing semi-closed greenhouse climate control performance (Hortinergy / ISHS-style semi-closed greenhouse literature).

> Avoiding air replacement to remove excess humidity is equivalent to about 6 l/h per 1000 m² of greenhouse under semi-arid conditions.

This scaling figure, applied to this greenhouse's ~5000 m², would suggest a much smaller ~30 kg/h
-- but it describes avoided ventilation-driven loss under specific semi-arid conditions, not a
dehumidification unit's rated capacity, so it wasn't used directly.

## Value used

**75 kg/hour** — the semi-closed greenhouse measurement, at the upper end of the found range and a
reasonable order of magnitude for an active system serving a greenhouse this size (~5000 m²),
larger than a single DryGair DG-12 unit's 48 kg/h (a real installation would likely use multiple
units or a larger combined system). **PLACEHOLDER**, not a measured spec for this greenhouse's
actual OptiClima unit — replace once the vendor provides a real capacity figure. See
`docs/assumptions/climate-control.md`.
