# Frontend redesign — greenhouse cross-section schematic + zone navigation

**Status:** Approved 2026-08-21, ready for `writing-plans`.

## Goal

Make the frontend "look more like an actual greenhouse" and feel more serious/professional, in the style of real greenhouse control software (Priva, Hoogendoorn, and the OptiClima system referenced in the Geothermiki vendor quote), rather than a generic parameter-slider form.

## Decisions (from brainstorming Q&A)

1. **What "looks like a greenhouse" means:** combine (a) a professional control-system dashboard layout and (b) a schematic of the greenhouse itself with live values overlaid — not just one or the other.
2. **Visual tone:** light, "clinical-industrial" (like Priva/Hoogendoorn software) — not a dark SCADA/control-room theme.
3. **Schematic viewing angle:** cross-section (one bay), matching the arch drawing in the Geothermiki S192G quote — cover, thermal screen, gutter/roof line, vents.
4. **Navigation model:** tabbed/zone navigation — clicking a zone on the schematic scrolls to and highlights that zone's controls/charts below, rather than a static header image or a hide/show accordion. Sections stay all visible (not hidden) — the click is a shortcut, not a toggle — since the app's data isn't heavy enough to need progressive disclosure and hiding sections would lose the "process view" feel of a real control system.

## Zones (functional, not physical — the model is single-zone)

Since the climate model simulates one shared air volume, "zones" map to the model's functional sub-systems, each with its own schematic hotspot, live pins, and matching panel section below:

| # | Zone | Schematic element | Live pins | Panel section (existing groups it maps to) |
|---|---|---|---|---|
| 1 | Cover & structure | Roof/wall arch | Outdoor temp, solar radiation | Κλίμα (structural/cover-related sliders) |
| 2 | Thermal screen | Horizontal line inside arch | Fixed energy-saving % (product spec, not adjustable), deployment schedule | Υγρασία (`day_start_hour`/`day_end_hour`) |
| 3 | Air / climate | Canopy-level pin | Indoor temp, RH, VPD, CO2 | Κλίμα, Υγρασία |
| 4 | Crop / canopy | Stylized plant row along gutter line | LAI, yield-to-date | Καλλιέργεια |
| 5 | Vents & dehumidification | Roof vent symbols | Vent state, condensation/dehumidification rate | Υγρασία (`dehumidification_setpoint_pct`) |

Clicking a zone's hotspot on the schematic scrolls the page to `#zone-<name>` and applies a highlight class to both the schematic group and the target section (cleared on next click or after a timeout). Existing `SLIDER_GROUPS` get reordered top-to-bottom to match the schematic's top-to-bottom order (cover/structure → screen → air/climate → crop → vents), and each wrapped section gets the matching `id`.

## Visual style

- **Background:** light off-white/grey (not pure white), flat white cards with a thin 1px border — no heavy shadows.
- **Color mapping (consistent everywhere — pins, slider accents, chart lines):** blue = temperature, teal/cyan = humidity/RH/VPD, green = CO2/crop, amber = warnings/out-of-range only (e.g. RH > 85%). Never used decoratively.
- **Typography:** IBM Plex Mono for numeric live-value readouts (pins, key stats) — already used in `docs/model-map.html`; IBM Plex Sans for labels/body text.
- **Status badges:** small pill labels in muted filled backgrounds for normal states (e.g. "ΣΚΙΑΣΤΡΟ: ΑΝΟΙΧΤΟ"); amber/red reserved strictly for genuinely out-of-range values.
- **Theming:** keep the existing CSS custom-property light/dark token structure; the light theme is the one being designed carefully here, dark inherits from existing tokens.

## Implementation shape

- New component `frontend/src/GreenhouseSchematic.tsx`: inline SVG, static geometry (arch/cover/screen/vents/gutter drawn once), with the 5 zone hotspots as SVG `<g>` elements (transparent hit-area + `onClick`). Live pins are small rounded-rect callouts (IBM Plex Mono value + unit) driven by props from the latest simulation data — same approach as `docs/model-map.html`'s inline SVG, no canvas/diagram library.
- `App.tsx`: add a slim top bar (app title + one-line status: current day, yield-to-date) above the schematic. Wrap each of the 4 `SLIDER_GROUPS` (reordered) and their charts in `<section id="zone-...">`. Add `activeZone` state; hotspot clicks call `scrollIntoView` + set the highlight class.
- No backend/API changes needed — reuses fields already returned (`rh_in_pct`, `vpd_kpa`, condensation/dehumidification fields, LAI/yield series).
- `ParamSlider` and chart components keep their internal structure; only wrapper/section styling and color tokens change.

## Out of scope for this change

Multi-zone modeling, real sensor data, disease-risk display, and any backend changes — this is a frontend presentation redesign only, built on data the API already exposes.
