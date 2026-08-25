# Fan-and-pad evaporative cooling: efficiency and wet-bulb formula

- **Type:** Web search aggregation (extension publications + peer-reviewed formula)
- **Retrieved:** 2026-08-25, via web search
- **Used for:** `twin/params.py` (`ClimateControlParams.fan_pad_efficiency`) and `twin/climate_model.py` (`_wet_bulb_temp_c`, `_fan_pad_outdoor_conditions`)

## Data used

**Cooling/saturation efficiency:**

> A properly designed, installed and maintained fan-and-pad cooling system may have an efficiency of up to 85%.

Source: UF/IFAS Extension, *"Fan and Pad Greenhouse Evaporative Cooling Systems"* (CIR1135/AE069), https://ask.ifas.ufl.edu/publication/AE069

> Fan and pad saturation efficiency ranged from 58% to 75% due to variable solar heat load and dynamic seasonal climatic conditions.

Source: Alabama Cooperative Extension System, *"Greenhouse Cooling: An Overview of Fan and Pad Systems"*, https://www.aces.edu/blog/topics/crop-production/greenhouse-cooling-an-overview-of-fan-and-pad-systems/

Taken together, real-world reported efficiency spans roughly 58-85%, with well-designed/well-maintained systems commonly cited at 70-85%. **`fan_pad_efficiency: 0.80`** in `twin/params.py` is a representative value within that "well-maintained" sub-range — **SOURCED** to this general range, not to a specific measurement of the greenhouse's own (not-yet-installed) system. See `docs/assumptions/climate-control.md`.

**Wet-bulb temperature formula:**

Stull, R. (2011), *"Wet-Bulb Temperature from Relative Humidity and Air Temperature"*, Journal of Applied Meteorology and Climatology, 50(11), 2267–2269. An empirical polynomial/trigonometric approximation of wet-bulb temperature from dry-bulb temperature and relative humidity, avoiding an iterative psychrometric solve. Used directly (verbatim formula) in `_wet_bulb_temp_c`. Standard meteorological formula, not a model assumption.
