# Canopy self-shading (Beer-Lambert integrated photosynthesis) and real-world yield benchmarks

- **Type:** Standard analytical result (crop-modeling literature) + web search aggregation (yield benchmarks)
- **Retrieved:** 2026-08-25
- **Used for:** `twin/crop_model.py` (`_canopy_light_response`)

## Data used

**Integrated canopy photosynthesis formula:**

The standard result for integrating a Michaelis-Menten (or similarly saturating) single-leaf
light response `f(I) = I/(I+K)` over a canopy where light attenuates with depth per Beer's law,
`I(z) = I0 * exp(-k*z)` for depth `z` in `[0, LAI]`:

```
∫[0,LAI] f(I(z)) dz = (1/k) * ln[(I0 + K) / (I0*exp(-k*LAI) + K)]
```

This is a well-known result in canopy photosynthesis modeling — the same style of integration
used in de Wit (1965) and Goudriaan's canopy photosynthesis formulations, and in the broader
"big-leaf" vs. multi-layer canopy modeling literature. It replaces a flat
`single_leaf_rate * LAI` multiplication, which implicitly assumes every leaf layer receives the
same unattenuated incident light — physically wrong for any real canopy, and the bug this fix
addresses (see `docs/assumptions/crop-model.md`, "Bug fix: canopy photosynthesis ignored
self-shading"). `k` reuses the project's existing, separately-sourced
`CANOPY_LIGHT_EXTINCTION_COEFF` (`papers/tomato-canopy-extinction-coefficient.md`).

**Real-world yield benchmarks (used to catch the bug, not a model parameter):**

> In the Dutch case, high-tech greenhouse tomato yield is 116 kg/m²/year per plantable area... Large-fruited tomatoes: the average annual yield can reach 75 kg/m² without artificial lighting, and over 90 kg/m² with artificial lighting... A new record yield for a Dutch greenhouse reached 121 kg per m².

Sources: [hortidaily.com — "New record yield for Dutch greenhouse: 121 kg per m2"](https://www.hortidaily.com/article/9379440/new-record-yield-for-dutch-greenhouse-121-kg-per-m2/), [upuper.com — industry summary of Dutch smart greenhouse tomato yields](https://upuper.com/industry_information/The-output-per-square-meter-reaches-70-kg-Decipher-the-reason-for-the-high-yield-of-tomatoes-in-Dutch-smart-greenhouses.html)

These figures aren't wired into the model as a parameter — they were the sanity check that first
flagged the self-shading bug: a 300-day run (no supplemental lighting in this greenhouse) was
producing yields at the Dutch **record** level, which requires artificial lighting real Dutch
growers use to hit that number. After the fix, the same run's annualized yield (~52 kg/m²/year)
sits below the "without artificial light" figure (~75 kg/m²/year), which is directionally
sensible for a Greek greenhouse without supplemental lighting.
