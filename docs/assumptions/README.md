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

## Research method note

Sources were located via web search on 2026-08-19 and are consumer-web references (research papers, university extension publications, industry sites), not a systematic literature review. Where a range was found rather than a single number, the config value is checked against that range, not against one paper's specific result. Treat "SOURCED" as *"checked against publicly available literature and found plausible,"* not as *"this specific greenhouse was measured and this is its true value."* Real calibration still requires this greenhouse's own sensor and yield data once it exists.
