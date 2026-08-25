# Greenhouse electricity consumption: dehumidification and ventilation fans

- **Type:** Web search aggregation (commercial product spec + measured fan benchmarks)
- **Retrieved:** 2026-08-25, via web search
- **Used for:** `twin/params.py` (`ClimateControlParams.dehumidification_specific_power_kwh_per_kg`,
  `ClimateControlParams.ventilation_specific_fan_power_w_per_m3h`)

## Context

First phase of an economic layer: physical electricity consumption (kWh) for the greenhouse's
two largest expected electrical consumers, per the user's own priority ranking after reviewing
the vendor quote's equipment list (`geothermiki-s192g-quote.md`) — the OptiClima cooling/
dehumidification system, and the fan-pad ventilation system. Not yet priced in €.

## Dehumidification: kWh per kg water removed

> The DG-12 50Hz Standard consumes 9.55 kW and delivers an efficiency of 4.5 liters of water
> extracted per kilowatt-hour.

Source: [DG-12 50Hz Greenhouse Dehumidifier](https://drygair.com/dehumidifiers/dg-12-50hz-standard/),
DryGair product spec page.

4.5 kg/kWh inverts to **≈0.22 kWh/kg**. This is the same DryGair DG-12 unit whose *capacity*
(kg/hour) was already rejected as a scale mismatch for this greenhouse's dehumidification
capacity parameter (see `greenhouse-dehumidification-capacity.md`) — that rejection was about
physical unit *size* (a portable unit undersized for a 5,000 m² greenhouse), not about the
underlying refrigerant-cycle dehumidification technology's electrical efficiency, which is a
property of the technology/cycle rather than of how big a single unit is built. Reusing the
efficiency ratio while having rejected the capacity is therefore a deliberate, separate call, not
an inconsistency.

A second source (a fan-coil dehumidification research system) reported an even better ratio:

> One study on a condensation dehumidification system with fan-coil units for greenhouses achieved
> a cooling COP of 24.1 [...] consumed only 0.11 kWh of electricity per kilogram of water removed.

Source: aggregated from a ScienceDirect study on condensation dehumidification with fan-coil units
using a low-cost cold source. **Not used** — a COP of 24.1 is characteristic of a specialized
experimental system using an external cheap cold source (e.g. geothermal or well water), not a
representative commercial packaged unit like the OptiClima quote describes; using it here would
understate real electricity cost for equipment closer to what's actually quoted.

## Ventilation: specific fan power (W per m³/h)

> An older standard 1~230V fan moved 5,350 m³/h with a power consumption of 240W (~0.045 W per
> m³/h). A newer energy-efficient fan moves 4,850 m³/h at 119W (~0.025 W per m³/h). A more powerful
> 7,000 m³ line fan moves 6,450 m³/h with 190W (~0.029 W per m³/h).

Source: [Save Energy in Your Greenhouse with Efficient Fan Choices](https://www.vostermans.com/ventilation/blog/how-can-i-save-energy-in-a-greenhouse),
Vostermans Ventilation blog (real product specs).

Took the middle of this ~0.025–0.045 W/(m³/h) span: **0.03 W per m³/h**. Applied only to the
*active* (above-baseline) portion of ventilation airflow, and only in hours the model's
`fan_pad_active` flag is true — the vendor quote's actual roof vents are described as continuous,
motorized (rack & pinion) but naturally/passively driven, not forced-air fans, so baseline
ventilation is not treated as an electrical load. This price only applies to the fan-pad system's
own forced-air fans, per the model's existing `fan_pad_cooling_enabled` toggle.

**SOURCED** to real, if generic, product benchmarks for both figures — not measured specs for
this specific greenhouse's actual installed equipment. See `docs/assumptions/economics.md`.
