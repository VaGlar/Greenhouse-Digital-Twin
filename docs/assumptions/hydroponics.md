# Hydroponics assumptions

`config/greenhouse_example.yaml` → `hydroponic:` block (`twin/params.py`'s `HydroponicParams`).
Implemented in three planned levels (agreed with the user 2026-08-26) — this file covers Level A,
completed; Levels B and C are tracked as open gaps in `README.md`, not yet started.

## System-type correction (2026-08-26)

`hydroponic.system_type` was `"NFT"` (Nutrient Film Technique) — a placeholder flag from v1 that
was never checked against real practice. NFT is standard for leafy greens/lettuce, not
indeterminate high-wire tomato: real commercial tomato greenhouses (and this project's own
Northern Greece precedent, Θερμοκήπια Σαββίδη / Dramello Fresh, plus this project's own vendor
quote's Spagnol BravoJet EC/pH fertigation equipment — see
`docs/papers/tomato-variety-selection-northern-greece.md` and
`docs/papers/geothermiki-s192g-quote.md`) use **drip-irrigated substrate** (rockwool or coco
slabs). Corrected to `"drip_substrate"`, with a new `substrate_type: "rockwool"` field
(descriptive only — doesn't yet feed the physics; coco is the other common choice).

## Level A: physical fertigation consumption

The three previous "physical, not yet priced" electricity systems (dehumidification,
ventilation, recirculation fans — see `economics.md`) get a fourth: the fertigation dosing pump.
Unlike those three, this one also tracks water and fertilizer mass, not just electricity.

| Parameter | Value | Tag | Notes |
|---|---|---|---|
| `ec_target_ms_cm` | 3.0 | **SOURCED** | 2.0-3.5 mS/cm is the commonly cited target range for greenhouse tomato nutrient solution. Was already shown (2.5-3.5) as a purely informational reference value in the frontend's "Συνταγή γεωπονίας" tab before this work — now a real `HydroponicParams` field the physics actually reads. Source: `docs/papers/hydroponic-fertigation-level-a.md`. |
| `ph_target` | 6.0 | **SOURCED** | 5.5-6.5 is the standard nutrient-availability optimum (outside this range, specific nutrients become chemically unavailable to the plant even if present in solution). Not yet wired into any model behavior — pH's effect is much more a hard availability threshold than a continuous dial, and no PH-driven yield/quality mechanism has been added (candidate for Level B/C). Source: same as above. |
| `drainage_target_fraction` | 0.25 | **SOURCED** | 20-30% leaching fraction is standard substrate-culture practice — irrigating somewhat beyond what the plant will actually use, so the excess flushes accumulated salts out of the root zone rather than letting them concentrate over time. Source: same as above. |
| `irrigation_pump_specific_power_kwh_per_m3` | 0.28 | **SOURCED (general average, not this specific pump)** | A global study on irrigation energy footprints finds drip irrigation averages ~1.0 MJ/m³ (≈0.28 kWh/m³), noticeably lower than sprinkler (1.8 MJ/m³) thanks to drip's lower operating pressure. This is a general drip-irrigation figure across agriculture broadly (includes water sourcing/conveyance in some of the underlying data), not a spec for this greenhouse's actual Spagnol BravoJet pump — flagged as an approximation, not a real product spec. Source: `docs/papers/hydroponic-fertigation-level-a.md`. |
| `fertilizer_g_per_l_per_ec_unit` | 0.64 | **PLACEHOLDER** | Generic EC-to-TDS conversion factor (EC in mS/cm × ~640 ≈ TDS in ppm/mg per liter, using the commonly-cited "0.64 scale" — other conventions use 0.5 or 0.7). This converts EC into an approximate fertilizer *mass* dosed, but real dosing depends on the specific fertilizer blend's composition, which isn't available for the real BravoJet system's actual fertilizer choice. Treat `total_fertilizer_dosed_kg` as an order-of-magnitude estimate, not a real quote-able mass. |

### Derivation (not new crop-model physics — a reporting/derivation layer, same pattern as the electricity fields in `economics.md`)

Irrigation volume is tied to the crop model's own transpiration output (`twin/crop_model.py`'s
`transpiration_kg_m2_hour`, already computed every hour for the humidity balance) plus the
leaching fraction above — matching how a real drip-substrate system is actually scheduled (dose
somewhat beyond what the plant will use, on purpose):

```
irrigation_water_kg_per_hour = transpiration_kg_per_hour / (1 - drainage_target_fraction)
drainage_water_kg_per_hour   = irrigation_water_kg_per_hour - transpiration_kg_per_hour
fertigation_elec_kw          = (irrigation_water_kg_per_hour / 1000) * irrigation_pump_specific_power_kwh_per_m3
fertilizer_dosed_g_per_hour  = irrigation_water_kg_per_hour * ec_target_ms_cm * fertilizer_g_per_l_per_ec_unit
```

(Water density ~1000 kg/m³, so kg and liters are interchangeable here.) Aggregated in
`api/main.py` the same way as the electricity fields: `irrigation_water_l_day` /
`drainage_water_l_day` / `fertilizer_dosed_g_day` are daily *totals* (a grower thinks in
liters/kg per day, not an average hourly rate); `fertigation_elec_kw` is a daily *mean rate*
like the other electricity fields, so it stays comparable to them on the same chart.
`total_fertigation_elec_kwh` is folded into `summary.total_electricity_kwh` alongside
dehumidification/ventilation/recirculation.

**Known simplification**: irrigation is purely demand-following (zero at night, since
transpiration is zero with no light) — no baseline/maintenance irrigation shot is modeled for
substrate moisture upkeep between light hours, which some real systems do run. Consistent with
how this model already treats ventilation/dehumidification as need-based rather than
scheduled.

## Level B and C — planned, not started

See `README.md`'s "Known open gaps" for the roadmap: Level B is the EC→fruit-weight/quality link
(the one piece that would make hydroponics actually change what the crop *grows*, not just what
it *costs*); Level C is deeper substrate/nutrient-specific modeling, considered lower priority
for now (same reasoning as senescence/leaf-abscission being left out — the added complexity
wouldn't be backed by a specific, sourced mechanism).

The structural work in this Level A pass (`HydroponicParams` becoming a real dataclass with
`ec_target_ms_cm`/`ph_target`/`drainage_target_fraction` as first-class fields, rather than a
single descriptive string) is what makes Level B a config/physics addition later, not a
re-plumbing job.
