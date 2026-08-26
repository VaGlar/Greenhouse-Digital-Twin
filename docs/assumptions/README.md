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
- [`weather.md`](./weather.md) — synthetic weather generator, and the real "typical year" data source added 2026-08-24 (not yet active — needs `scripts/fetch_weather.py` run from an environment with internet access)
- [`economics.md`](./economics.md) — economic layer, phase 1: physical electricity consumption (dehumidification + ventilation), not yet priced
- [`../model-map.html`](../model-map.html) — visual wiring map of how config/weather/climate model/crop model/API/frontend connect (open in a browser; also published as a shareable [Claude artifact](https://claude.ai/code/artifact/7e7a74eb-ed2c-4a83-9a5d-b8639eedc3b5))

## Going forward

New assumptions get the same treatment at the point they're introduced: a short comment in the code/config citing where the number comes from (source + page/section if it has one, or "engineering estimate — no single source" if it doesn't), and an entry in the relevant file here. This audit is meant to stay current, not be a one-time snapshot — if a value here gets changed later, update both the code comment and this doc in the same commit.

## Known open gaps (not yet modeled)

Distinct from the tables above — these are things the model doesn't attempt to represent at all yet, tracked here so they don't get lost:

- **Senescence / leaf abscission** (`twin/crop_model.py`) — real plants shed old leaves/tissue as they age (permanent biomass loss), on top of the day-to-day respiration the model does track (fixed 2026-08-20, see `crop-model.md`). Not modeled — but investigated 2026-08-25 and found lower-priority than it looked: real indeterminate tomato growers actively deleaf (remove old leaves continuously as new ones grow), and no quantitative literature was found for an age-driven decline rate in long-cycle greenhouse tomato either way. The model's flat LAI plateau after canopy closure isn't clearly wrong for a well-managed crop; adding a decline curve now would just be an unsourced guess, so left undone rather than adding another unsourced number.
- **Latitude-driven day length** (`twin/weather.py`) — `weather.latitude_deg` is stored but unused; the synthetic weather generator uses flat calendar-day/hour sinusoids instead of real sun-angle geometry. See `weather.md`.
- **Fixed day/night clock window** (`climate_control.day_start_hour/day_end_hour`) — a flat 6am-8pm boundary, not tied to actual sunrise/sunset for the real site/season. See `climate-control.md`.
- **Disease risk still not modeled** — RH/VPD now feed photosynthesis (2026-08-20, see `crop-model.md`), which is a prerequisite for a future disease-risk module (Botrytis/powdery mildew both depend heavily on RH), but that module itself doesn't exist yet.
- **Economic layer is physical-only so far** (`economics.md`) — dehumidification and ventilation electricity are computed in kWh, but no €/kWh tariff, cost, or revenue figures exist yet; recirculation fans and fertigation pumps (both real consumers per the vendor quote) aren't modeled at all.
- **`crop.variety` is a researched label, not a model input yet** (`crop-model.md`) — a real, regionally-plausible beef tomato class (EYRE RZ F1) was chosen after checking agronomic fit, market demand, and a real Northern Greece precedent, but no crop-model parameter is keyed to it yet. Planned: make variety-dependent traits (target fruit weight, truss rate, fruit-set temperature tolerance) into tunable parameters sourced to this default, so swapping the variety later means changing values, not the model.

## Research method note

Sources were located via web search on 2026-08-19 and are consumer-web references (research papers, university extension publications, industry sites), not a systematic literature review. Where a range was found rather than a single number, the config value is checked against that range, not against one paper's specific result. Treat "SOURCED" as *"checked against publicly available literature and found plausible,"* not as *"this specific greenhouse was measured and this is its true value."* Real calibration still requires this greenhouse's own sensor and yield data once it exists.
