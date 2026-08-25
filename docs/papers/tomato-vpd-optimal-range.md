# VPD and CO2 coordination in greenhouse tomato photosynthesis

- **Type:** Web search aggregation, referencing a Scientific Reports study on VPD/CO2 coordination in greenhouse tomato, plus general VPD-stress literature
- **Retrieved:** 2026-08-20, via web search
- **Used for:** `VPD_MIN_KPA`, `VPD_OPT_KPA`, `VPD_MAX_KPA` (twin/crop_model.py)

## Data used

> The optimal VPD range recommended in different studies is from 0.3 kPa to 1.0 kPa. When VPD is within 0-1 kPa, photosynthesis is positively related to VPD, with higher Pn found when VPD is approximately 1 kPa. A suitable VPD for tomato growth is less than 2 kPa. Photosynthesis decreases markedly with increasing VPD from 1 to 1.5 kPa; VPD between 1.5-2 kPa is known to reduce stomatal conductance for horticultural crops.

Used VPD_MIN=0.2 kPa (just below the cited 0.3 floor), VPD_OPT=0.85 kPa (mid of the 0.3-1.0 optimal range, near the reported ~1 kPa peak), VPD_MAX=2.0 kPa ("suitable... less than 2 kPa") in a bell-shaped response multiplying gross photosynthesis, structurally identical to the existing temperature response curve.

Source article referenced in search results: [Coordination between vapor pressure deficit and CO2 on the regulation of photosynthesis and productivity in greenhouse tomato production](https://www.nature.com/articles/s41598-019-45232-w) (Scientific Reports, open access) — full text not fetched directly from this environment, figures taken from search-result summary.
