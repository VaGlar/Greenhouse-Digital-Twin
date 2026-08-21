# Ideal relative humidity conditions for greenhouse tomatoes

- **Publisher:** DryGair (greenhouse dehumidification equipment company, technical blog)
- **URL:** https://drygair.com/blog/what-are-the-ideal-conditions-for-greenhouse-tomatoes/
- **Type:** Web article (not paginated)
- **Retrieved:** 2026-08-20, via web search
- **Used for:** `climate_control.dehumidification_setpoint_pct` (config default in twin/params.py)

## Data used

> Production guides for greenhouse tomatoes vary somewhat in their recommendations for optimal RH: anywhere from 60% to 85%. During the day, tomato plants may enjoy higher humidity levels of 80-85% RH, however during the night, humidity levels of 65-75% are ideal.
>
> The optimum relative humidity for pollination is 70%. At RH levels above 80%, pollen grains start to stick together, reducing dispersal and lowering pollination rates; at RH levels below 60%, the stigma can dry out, also lowering pollination rates.
>
> The optimal range of VPD is between 4 and 8 mbar (~0.4-0.8 kPa); higher VPD may be better during later developmental stages such as flowering, where optimal VPD can reach 1.2 kPa.

Used **70%** as the single `dehumidification_setpoint_pct` value (the model doesn't yet split day/night RH targets) — the one figure in this range the source calls an actual optimum (for pollination) rather than a range endpoint. Corrected from an earlier, uncited 85% guess on 2026-08-20 once the user asked for the literature-defined value specifically.
