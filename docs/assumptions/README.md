# Model assumptions — audit and sources

Every numeric parameter in this project falls into one of three buckets:

| Tag | Meaning |
|---|---|
| **SITE-SPECIFIC** | A real design value for *this* greenhouse (area, CHP size). Not "wrong," just needs confirming against the final build. |
| **SOURCED** | A literature/engineering value with an actual citation, checked against real references. Reasonable to trust as a starting point. |
| **PLACEHOLDER** | An engineering rule-of-thumb or an educated guess with no specific citation behind it yet. Lowest confidence — should be the first thing recalibrated once real sensor/yield data exists. |

This folder is the audit trail for every non-obvious number in `config/greenhouse_example.yaml` and the `twin/` model constants. Each file below covers one model area. Where a value is **SOURCED**, the corresponding code/config comment cites the same source — this doc is the long-form version, the code comment is the short pointer.

**Files:**
- [`geometry-and-chp.md`](./geometry-and-chp.md) — greenhouse shell, CHP unit
- [`climate-control.md`](./climate-control.md) — setpoints, ventilation, CO2 dosing
- [`crop-model.md`](./crop-model.md) — photosynthesis, growth, yield (`twin/crop_model.py`)
- [`weather.md`](./weather.md) — synthetic weather generator

## Going forward

New assumptions get the same treatment at the point they're introduced: a short comment in the code/config citing where the number comes from (source + page/section if it has one, or "engineering estimate — no single source" if it doesn't), and an entry in the relevant file here. This audit is meant to stay current, not be a one-time snapshot — if a value here gets changed later, update both the code comment and this doc in the same commit.

## Known open gaps (not yet modeled)

Distinct from the tables above — these are things the model doesn't attempt to represent at all yet, tracked here so they don't get lost:

- **Senescence / leaf abscission** (`twin/crop_model.py`) — real plants shed old leaves/tissue as they age (permanent biomass loss), on top of the day-to-day respiration the model does track (fixed 2026-08-20, see `crop-model.md`). Not modeled — would matter most for long crop cycles (many months) where accumulated leaf drop becomes significant. No target date; revisit if long-cycle runs start looking unrealistically leafy/heavy late in the cycle.
- **Latitude-driven day length** (`twin/weather.py`) — `weather.latitude_deg` is stored but unused; the synthetic weather generator uses flat calendar-day/hour sinusoids instead of real sun-angle geometry. See `weather.md`.
- **Fixed day/night clock window** (`climate_control.day_start_hour/day_end_hour`) — a flat 6am-8pm boundary, not tied to actual sunrise/sunset for the real site/season. See `climate-control.md`.
- **Condensation/dehumidification** (`twin/climate_model.py`, added 2026-08-20) — the new humidity model caps vapor pressure at saturation (100% RH) instead of modeling condensation on the cover or active dehumidification (relevant to the real quote's OptiClima cooling/dehumidification panels). See `crop-model.md`.
- **Humidity doesn't feed back into crop growth yet** — RH/VPD are tracked and reported, but the crop model's photosynthesis/stomatal response still ignores them (no VPD-driven stomatal closure). A real refinement for later, and a prerequisite for a future disease-risk module (Botrytis/powdery mildew both depend heavily on RH).

## Research method note

Sources were located via web search on 2026-08-19 and are consumer-web references (research papers, university extension publications, industry sites), not a systematic literature review. Where a range was found rather than a single number, the config value is checked against that range, not against one paper's specific result. Treat "SOURCED" as *"checked against publicly available literature and found plausible,"* not as *"this specific greenhouse was measured and this is its true value."* Real calibration still requires this greenhouse's own sensor and yield data once it exists.
