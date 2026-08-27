# Hydroponic fertigation Level A: EC/pH/drainage targets, pump energy, EC-to-mass conversion

- **Type:** Web search aggregation (extension publications, industry sites, a peer-reviewed
  global irrigation-energy study)
- **Retrieved:** 2026-08-26, via web search
- **Used for:** `twin/params.py` (`HydroponicParams`), `twin/simulate.py` (irrigation/drainage/
  fertigation derivation)

## EC / pH / drainage targets

- Tomato nutrient solution EC target range: commonly cited as 2.0-3.5 mS/cm across extension and
  hydroponics references (e.g. Missouri Extension's hydroponic nutrient solution guidance, general
  hydroponics EC guides). This project already showed 2.5-3.5 mS/cm as a purely informational
  reference value before this work (frontend "Συνταγή γεωπονίας" tab) — used the same range,
  midpoint 3.0, now as a real `ec_target_ms_cm` field.
- pH target: 5.5-6.5 is the standard nutrient-availability range cited across the same sources —
  outside it, specific macro/micronutrients become chemically less available to the plant even
  when present in solution.
- Drainage/leaching fraction: 20-30% is standard substrate-culture practice, cited across
  hydroponic substrate-culture guidance (Penn State Extension's hydroponic nutrient concentration
  methodology, general substrate-culture references) — irrigating somewhat beyond plant demand so
  the excess flushes accumulated salts out of the root zone.

Sources: [MU Extension — Hydroponic Nutrient Solutions](https://extension.missouri.edu/publications/g6984),
[Penn State Extension — Hydroponics systems: calculating nutrient solution concentrations](https://extension.psu.edu/hydroponics-systems-calculating-nutrient-solution-concentrations-using-the-two-basic-equations).

## Irrigation pump specific energy (kWh/m³)

> Drip irrigation has an average energy intensity of 1.0 MJ/m³ [...] Sprinkler irrigation is the
> most energy-intensive at 1.8 MJ/m³, while surface irrigation is the least intensive at 0.5
> MJ/m³. [...] Electric pumping has an energy intensity of 0.5 MJ/m³, while diesel pumping is more
> energy-intensive at 1.2 MJ/m³.

1.0 MJ/m³ ≈ 0.278 kWh/m³ (1 kWh = 3.6 MJ) — used as 0.28.

Source: [Global energy use and carbon emissions from irrigated agriculture — Nature
Communications](https://www.nature.com/articles/s41467-024-47383-5) (peer-reviewed, global study
across irrigation methods and energy sources).

**Caveat**: this is a broad, cross-agriculture average for drip irrigation generally (the
underlying global dataset spans field agriculture, not specifically small pressurized greenhouse
fertigation loops, and may include some water-sourcing/conveyance energy upstream of the
greenhouse's own dosing pump). Used as a plausible order-of-magnitude figure, not a spec for this
greenhouse's actual Spagnol BravoJet pump (no real spec sheet available for that unit's power
draw).

## EC-to-fertilizer-mass conversion

> TDS (ppm) ≈ EC (mS/cm) × 500 (using 500 scale) or TDS (ppm) ≈ EC (mS/cm) × 700 (using 700
> scale). This is a commonly used rule of thumb for converting between electrical conductivity
> and total dissolved solids. [...] The actual fertilizer dosage needed to achieve a specific EC
> varies depending on the fertilizer formulation and composition, so a universal rule of thumb
> converting grams per liter per mS/cm may not be readily available in general references.

Used the midpoint-ish "0.64 scale" (a third commonly-cited EC-to-TDS conversion convention,
between the 500 and 700 scales quoted above) as `fertilizer_g_per_l_per_ec_unit = 0.64` —
explicitly flagged **PLACEHOLDER**, not SOURCED: the search itself confirms no single universal
factor exists, since real dosage depends on the specific fertilizer blend. `total_fertilizer_dosed_kg`
should be read as an order-of-magnitude estimate.

Source: [Atlas Scientific — What Is EC In Hydroponics?](https://atlas-scientific.com/blog/what-is-ec-in-hydroponics/),
general EC/TDS conversion guidance aggregated via web search.
