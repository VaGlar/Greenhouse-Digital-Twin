# Greenhouse electricity consumption: dehumidification and ventilation fans

- **Type:** Web search aggregation (commercial product spec + measured fan benchmarks)
- **Retrieved:** 2026-08-25, via web search
- **Used for:** `twin/params.py` (`ClimateControlParams.dehumidification_specific_power_kwh_per_kg`,
  `ClimateControlParams.ventilation_specific_fan_power_w_per_m3h`,
  `ClimateControlParams.recirculation_fan_power_kw`)

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

## Recirculation (HAF) fan bank: how many, and how big

The vendor quote's ACF21 spec (508mm/20" diameter, 5,400 m³/h) matches real 20" HAF
circulation fans:

> HAF20110C: 1/10 HP, 115v, 1725 RPM, 2600 CFM. F5 Fans 20-inch: 1/3HP, 5470 CFM, 1725 RPM.
> Green Breeze HAF Fan: 20" diameter, 3,650 CFM, 1/3 HP.

Source: Griffin Greenhouse Supplies, F5 Fans, and J&D Manufacturing product listings (via web
search). Converting each to specific power (W ÷ m³/h) gives a range of **≈0.017–0.04 W/(m³/h)**
— a similar efficiency range to the exhaust/fan-pad fans above, on the more-efficient end since
HAF fans work against much lower static pressure than exhaust fans pushing air through vents or
wet pads:

> HAF fans are generally more energy-efficient than exhaust fans because they operate against
> low static pressure.

Source: aggregated from HAF-vs-exhaust-fan comparison articles (Bluelab, Rimol) via web search.

The quote gives no fan count for its "air recirculation" (€7,500) line item. The user shared the
quote's own fan-layout diagram — a racetrack circulation pattern (fans in each bay row blowing
alternating directions, air looping back via the next bay) — but its "≶" break symbols are a
standard drawing convention meaning the pattern repeats along the greenhouse's length, not a
literal count of the few fans drawn. So the diagram confirms the topology (one fan row per bay)
rather than giving a count directly. Estimated instead from real HAF spacing guidance:

> As a general guideline, one fan is required every 50 feet, with subsequent fans located 40'
> to 50' apart to keep the air mass moving.

Source: aggregated HAF installation guidance (Rimol, Farm Energy Extension) via web search.

Applied to this greenhouse's real geometry (5 bays × 100m length, from
`geothermiki-s192g-quote.md`): ~100m ÷ ~14m spacing ≈ **7 fans per row** (one row per bay) × **5
rows** = **35 fans**. At 5,400 m³/h each × an assumed 0.025 W/(m³/h) specific power (middle of the
measured range above): 35 × 5,400 × 0.025 / 1000 ≈ **4.7 kW** combined electrical draw when
running.

A generic commercial "8-10 CFM per square foot of floor area" sizing rule was also found and
explicitly **rejected**: applied to this greenhouse's ~53,800 sq ft floor area it implies ~146
fans, an implausible fan count for a real installation — the greenhouse-specific spacing rule
above is a much better fit for HAF fans specifically (that generic CFM/sq ft figure appears
intended for a different context, e.g. general air-exchange sizing, not HAF circulation density).

**PLACEHOLDER**: an estimated fan count/power, not a real spec for this installation's actual
recirculation fan bank. See `docs/assumptions/economics.md`.
