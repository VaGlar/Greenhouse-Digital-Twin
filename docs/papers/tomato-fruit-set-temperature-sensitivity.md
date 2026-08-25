# Tomato fruit-set temperature sensitivity (separate from photosynthesis tolerance)

- **Type:** Web search aggregation (extension/university publications)
- **Retrieved:** 2026-08-25, via web search
- **Used for:** `twin/crop_model.py` (`FRUIT_SET_T_MIN_C`, `FRUIT_SET_T_OPT_C`, `FRUIT_SET_T_MAX_C`, `_fruit_set_temp_response`)

## Data used

Found while investigating a bug the user caught: setting an unrealistically cold night setpoint
(down to 5°C) kept *raising* simulated yield with no floor, because nothing in the model
distinguished fruit-set temperature sensitivity from photosynthesis temperature tolerance —
`T_MIN_C=10, T_OPT_C=27, T_MAX_C=35` in this file are sourced specifically to photosynthetic
*rate*, which tomato leaves tolerate over a wide range. Fruit set — whether a flower actually
becomes a fruit — depends on pollen viability and pollen-tube growth, which are far more
temperature-sensitive:

**Low temperature (chilling):**

> Nighttime temperatures below 55 degrees F promote blossom drop. Low temperatures affect pollen viability as well as the growth rate of the pollen tube that forms shortly after a pollen grain lands on a mature stigma.

Source: [Understanding Tomato Fruit Set — Missouri Produce Growers Bulletin, University of Missouri IPM](https://ipm.missouri.edu/MPG/2013/4/Understanding-Tomato-Fruit-Set/)

**Optimal window:**

> Ideal fruit set occurs within a very narrow range of night temperatures (60°-70°F), which equals approximately 15.6-21.1°C.

Source: [Understanding High Temperature Effects on Fruit Set of Tomatoes — Purdue University Vegetable Crops Hotline](https://vegcropshotline.org/article/understanding-high-temperature-effects-on-fruit-set-of-tomatoes/)

**High temperature:**

> If tomato plants experience night temperatures above 75°F (approximately 24°C), interference with the growth of pollen tubes can occur preventing normal fertilization and causing blossom drop.

Same Purdue source as above.

## Values used

`FRUIT_SET_T_MIN_C = 12.0` (55°F ≈ 12.8°C, rounded down slightly for a smooth bell-curve floor),
`FRUIT_SET_T_OPT_C = 18.0` (midpoint of the cited 15.6-21.1°C ideal window, also matching this
project's own separately-sourced `heating_setpoint_night_c=17°C`), `FRUIT_SET_T_MAX_C = 24.0`
(75°F). These are deliberately much narrower than the photosynthesis cardinal temperatures in the
same file — a real, well-documented biological distinction, not an inconsistency.

Not sourced: `FRUIT_SET_TEMP_EMA_HALF_LIFE_HOURS = 12.0` (the exponential-moving-average window
this response is evaluated against, rather than the instantaneous hourly temperature) — an
engineering choice representing roughly how long flower/pollen-tube development integrates recent
conditions, not calibrated to a specific study. See `docs/assumptions/crop-model.md` for the full
writeup, including a known remaining gap: the resulting model's optimum night temperature (12°C)
doesn't yet land on the literature's 17-18°C, because a separate mechanism (respiration deficit,
also added 2026-08-25) still favors cooler nights via less biomass burned.
