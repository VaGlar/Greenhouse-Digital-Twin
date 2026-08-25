# Γεωθερμική α.ε — Τεχνική περιγραφή & ενδεικτικός προϋπολογισμός, θερμοκηπιακή μονάδα S192G (OptiClima)

- **Publisher:** Γεωθερμική α.ε (Ι. Μπάτσης Α.Ε), Θεσσαλονίκη
- **Ref:** GEO/GR/OPTIC/171024, 17 Οκτ. 2024
- **Type:** Real vendor quote — uploaded by the user, this is a PDF the user has locally (not a public URL)
- **Used for:** `geometry.height_m`, `geometry.cover_u_value_w_m2k` (material identification), `geometry.cover_transmissivity` (material identification), `geometry.cover_area_factor` — config/greenhouse_example.yaml

## Key data extracted (2026-08-19)

- Greenhouse unit: width 48m, bay width 9.6m (5 bays), length 100m, side height 4.0m, ridge/total height 6.5m, floor area 4,800 m² (+ 480 m² service room)
- Cover: double-inflated polyethylene, 180 micron, 3 layers exterior + 8 layers interior thermal/anti-drip film ("Πλαστικών Κρήτης")
- Ventilation: continuous double roof vents, 2.0m wide per bay, rack & pinion motorized, digital thermostat
- Insect screen: 40 mesh
- Thermal screen: type PH55, 55% shading, ~55% energy saving
- Recirculation fans: ACF21, 5,400 m³/h, 508mm diameter — claimed 47% heating efficiency improvement from uniform air distribution
- OptiClima system: semi-closed greenhouse climate system with cooling panels, dehumidification, ClimaBoxes (fan-heaters), CO2 enrichment, per-section 2.5m climate corridor
- Heating: gas burner, 7,000,000 kcal/h (~8,140 kW thermal) — **not used in this project**; the user confirmed no gas burner will be installed, CHP remains the sole heat source (2026-08-19 decision)
- Fertigation: Spagnol BravoJet, EC/pH controlled injection dosing, 4 fertilizer + 1 acid tank (1000L each), up to 600 l/h per zone
- Structural design loads: wind 120 km/h, snow 35 kg/m², crop hanging load 15 kg/m², 5-year steel frame warranty
- Indicative cost (ex-VAT): €729,500 total (structure €235,000, air recirculation €7,500, thermal screen €68,000, OptiClima system €195,000, hydroponics/irrigation €139,000, installation/transport €85,000)

## Note on internal inconsistency

The document states total area as "5.280 m²" on its cover page (4,800 greenhouse + 480 service room) but the pricing table's own line item reads "SERRA 192G 6393m²" — these don't reconcile with each other or with the 48m×100m=4,800m² dimensions given in section 2. **User decision (2026-08-19): keep `area_m2: 5000` in config regardless** — close to but not exactly matching either of the quote's own figures, per explicit instruction not to change it.

## Derivation used for `height_m` and `cover_area_factor`

Modeled the roof cross-section per bay as a circular arc with chord = bay width (9.6m) and sagitta/rise = ridge − side height (6.5 − 4.0 = 2.5m):
- Circle radius: R = chord²/(8·rise) + rise/2 ≈ 5.858m
- Arc length (per bay, per meter of building length): 2R·arcsin((chord/2)/R) ≈ 11.25m (vs. 9.6m flat chord)
- `height_m` (average interior height): side_height + rise·(2/3) ≈ 4.0 + 2.5·0.667 ≈ 5.67m (2/3 is the standard centroid-height approximation for a circular/parabolic arch segment)
- `cover_area_factor`: total cover area (5 bays' roof arcs × 100m + 2 long side walls × 4.0m height + 2 end walls approximated at average height) ÷ floor area (48×100=4,800m²) ≈ 6,970 / 4,800 ≈ **1.45**

This is a from-scratch geometric derivation from the quote's own dimensions, not an external literature citation — flagged as SOURCED in the sense of "computed from real design geometry," distinct from the literature-review sense used elsewhere.
