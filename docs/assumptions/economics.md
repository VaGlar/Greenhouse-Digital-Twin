# Economic-layer assumptions

First phase of an economic layer on top of the physical model, started 2026-08-25.
User decision: the CHP's electricity is **sold to the grid**, not self-consumed by
the greenhouse — the greenhouse draws 100% of its own electricity from the grid,
with no netting against CHP output. So the two sides (CHP revenue, greenhouse
electricity cost) are independent, not offsetting.

This first step only models **physical electricity consumption (kWh)** for the
greenhouse's two largest expected electrical consumers, identified by comparing
against a real vendor quote's equipment list
(`docs/papers/geothermiki-s192g-quote.md`) and general greenhouse-energy literature.
No electricity price or cost/revenue figures yet — those come in a later phase once
this physical layer is validated.

`config/greenhouse_example.yaml` → `climate_control:` block. Model code:
`twin/simulate.py` (per-hour), `api/main.py` (daily/season aggregation).

| Parameter | Value | Tag | Notes |
|---|---|---|---|
| `dehumidification_specific_power_kwh_per_kg` | 0.22 | **SOURCED** | Electrical energy per kg of water actually removed by the active dehumidification system. Taken from the DryGair DG-12's own published spec (9.55 kW drawn, ~45 kg/hour water removed → ~4.5 kg/kWh → ~0.22 kWh/kg). See `docs/papers/greenhouse-electricity-consumption.md`. Reused even though the DG-12's *capacity* was already rejected as a scale mismatch for this greenhouse (`climate-control.md`'s `dehumidification_capacity_kg_water_per_hour` row) — kWh-per-kg is a property of the refrigerant-cycle dehumidification technology itself, not of the unit's physical size/coverage area, so it transfers independently of that earlier capacity issue. |
| `ventilation_specific_fan_power_w_per_m3h` | 0.03 | **SOURCED** | Electrical power per unit of *active* (above-baseline) ventilation airflow. Only priced when `fan_pad_cooling_enabled` and ventilation is ramped above `vent_min_ach` — the real vendor quote describes the roof vents as continuous, motorized (rack & pinion) but passively/naturally driven, so baseline leakage ventilation is not treated as an electrical load; only the fan-pad system's forced-air fans are. 0.03 W per (m³/h) is the middle of a 0.025–0.045 W/(m³/h) range measured across real greenhouse ventilation fans (older vs. newer energy-efficient models). See `docs/papers/greenhouse-electricity-consumption.md`. |

## Modeling structure note

Both quantities are computed per simulated hour in `twin/simulate.py`, directly from
already-existing physical outputs of the climate model — no new physics, just a
derived economic-adjacent layer read off the existing state:

- **Dehumidification electricity** = `dehumidified_kg` (that hour) × `dehumidification_specific_power_kwh_per_kg` — ties electricity directly to water actually removed, so it responds to everything that already drives dehumidification workload (RH setpoint, ventilation-driven humidity swings — see `climate-control.md`'s cross-check note under `heating_setpoint_night_c`).
- **Ventilation electricity** = (active ACH above `vent_min_ach`) × greenhouse volume × `ventilation_specific_fan_power_w_per_m3h`, but only in hours where `fan_pad_active` is true (i.e. `fan_pad_cooling_enabled` and ventilation is actively ramped, not just passive leakage).

Aggregated in `api/main.py` the same way as `heat_used_kw` (daily mean for the kW
time series shown in charts, `sum() * timestep_hours` for the season total in kWh),
under `summary.total_dehumidification_elec_kwh`, `summary.total_ventilation_elec_kwh`,
and their sum `summary.total_electricity_kwh`.

## Known open gaps / not yet modeled

- **Not priced yet**: this is physical kWh only — no €/kWh electricity tariff, no
  cost or revenue figures. That's the next phase.
- **Recirculation fans (ACF21, per the vendor quote)** and **fertigation pumps
  (Spagnol BravoJet)** are real electrical consumers at this greenhouse that are
  not modeled at all yet — smaller than the two above, and would need new
  modeling (how many units, when they run / irrigation volume) rather than reuse
  of an existing physical output. Deferred as a later, lower-priority step.
- **CHP's own parasitic/auxiliary load** (control systems, its own cooling) is not
  modeled — out of scope for the greenhouse's own electricity bill since it's the
  CHP owner's concern, not the greenhouse's.
