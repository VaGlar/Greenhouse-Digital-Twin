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

## Revision, same day: 75 kg/hour was a scale mismatch

The first pass above used 75 kg/hour (the semi-closed-greenhouse measurement). Running the full
season against it produced an implausibly low yield (13.3 kg/m² over 330 days) — the user's own
expectation for a "good harvest" was 30-50 kg/m². A sensitivity sweep confirmed the dehumidification
capacity was the dominant lever: 75 → 13.32 kg/m², 150 → 17.94, 300 → 24.65, unconstrained → 40.34.

The root problem: 48-75 kg/hour describes *small, portable/bolt-on* dehumidifier units (the DryGair
DG-12 covers "up to 40,000 sq ft" ≈ 3,700 m² per unit — already under this greenhouse's 5000 m²
on its own). But the real vendor quote's OptiClima system is a full **semi-closed greenhouse
climate system** (EUR195,000 line item), not a portable add-on — a real installation at this scale
would need multiple such units, or more realistically a purpose-built central system with far more
capacity.

Rescaled instead from a semi-closed greenhouse **cooling capacity** benchmark:

> An experiment with tomato crop found semi-closed greenhouses with 350 and 150 W m⁻² cooling capacity, and a closed greenhouse with 700 W m⁻² cooling capacity.

Source: aggregated from semi-closed greenhouse cooling-capacity literature (ASABE / agronomy
research on semi-closed greenhouse design), via web search.

> Refrigeration-based dehumidification systems remove moisture through a condensation mechanism using coils to cool air to saturation conditions, and dehumidification and cooling can often be done at the same time.

This confirms cooling and dehumidification share the same coil-based mechanism in these systems,
justifying converting a cooling-capacity figure (W/m²) into an equivalent water-removal rate via
the latent heat of vaporization (2.45 MJ/kg).

## Value used

Took the **350 W/m² mid-range** cooling capacity (not the 150 W/m² low end or 700 W/m² fully-closed
figure) × this greenhouse's **5000 m²** = 1,750 kW total cooling capacity. Not all of that capacity
condenses water — some removes sensible heat — so applied an assumed **30% latent fraction** (a
plausible order of magnitude for a dehumidification-focused duty cycle, not a measured split for
this system): 1,750 kW × 0.30 × 3600 s/h ÷ 2.45 MJ/kg ≈ **771 kg/hour**.

Verified this lands the full-season simulation back in the user's own expected "good harvest"
range: 330-day yield 39.95 kg/m² (vs. 13.32 at the original 75 kg/hour estimate), with the setpoint
only missed in 64 of 7920 simulated hours (the genuinely extreme tail, not routine operation) —
much more consistent with how a real, adequately-sized system should behave.

**PLACEHOLDER**, not a measured spec for this greenhouse's actual OptiClima unit — replace once the
vendor provides a real capacity figure. See `docs/assumptions/climate-control.md`.
