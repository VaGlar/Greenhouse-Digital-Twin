# Tomato truss-formation rate benchmark, and why it doesn't apply directly to large-fruit beef tomato

- **Type:** Web search aggregation (industry/extension publications) + derived cross-check
- **Retrieved:** 2026-08-26, via web search
- **Used for:** `docs/assumptions/crop-model.md` (correcting the `avg_truss_rate_per_week` /
  `steady_state_truss_rate_per_week` cross-check, `api/main.py`)

## Why this exists

`docs/assumptions/crop-model.md`'s 2026-08-26 cross-check originally compared this model's
derived `avg_truss_rate_per_week` (~0.27/week) against "the ~1/week (stable 24h temperature) real
commercial benchmark cited in `docs/papers/tomato-variety-selection-northern-greece.md`" — that
citation was checked directly and the figure does not actually appear in that file. This paper
supplies (and corrects) the real benchmark.

## Data used

> A new truss forms almost every seven days, with harvest following six to seven weeks later, and
> this cycle repeating for roughly 40 weeks each year.

Source: [Your Guide to High-Wire Tomato Growing — Greenhouse Grower](https://www.greenhousegrower.com/production/your-guide-to-high-wire-tomato-growing/)

> Beefsteak tomatoes, which are slower growing tomato types, are typically lowered one turn per
> week in high-wire growing systems... in contrast to faster-growing varieties like cherry
> tomatoes, which are lowered more frequently.

Same source. This is a stem-elongation/lowering cadence, not a harvested-truss-mass rate — it
does not by itself say how much fruit mass each truss carries.

## Why ~1/week is the wrong number to compare this model against directly

~1 truss/week is a generic, roughly fruit-size-independent *truss-formation* pace cited for
high-wire tomato in general. Plugging it directly into this project's own `target_fruit_weight_g`
(255g) and `fruits_per_truss` (5, both `CropParams`, see `docs/papers/tomato-variety-selection-northern-greece.md`)
and `stems_per_plant` x `density_plants_per_m2` (2.5 stems/m² default) gives an internally
implausible result:

```
1 truss/week x 5 fruit/truss x 255 g/fruit x 2.5 stems/m² x 40 production weeks/year
  = 127.5 kg/m²/year
```

That's above the Dutch all-time greenhouse tomato yield record (121 kg/m²/year, see
`docs/assumptions/crop-model.md`'s "Bottom line" section) for what should be a below-record
Greek greenhouse without supplemental lighting.

## A self-consistent benchmark instead

Working backward from this project's own already-sourced real annual yield benchmark for
beef/TOV-type greenhouse tomato (65-70 kg/m²/year, see `docs/assumptions/crop-model.md`'s
"Bottom line" section) using the same `target_fruit_weight_g`/`fruits_per_truss`/stem-density
assumptions:

```
65,000-70,000 g/m²/year / 2.5 stems/m² / (255 g x 5 fruit/truss)
  = 20.4-21.9 trusses/stem/year
  / ~40 production weeks/year
  = ~0.5-0.55 trusses/stem/week
```

So **~0.4-0.5/week** (allowing some margin) is the truss rate actually implied by this project's
own real-world yield benchmark for large-fruited beef tomato — not ~1/week. Large fruit needs
proportionally more assimilate per truss than a smaller-fruited round or cherry variety, so a
slower truss-completion rate at the same total yield is expected, not a modeling error.

## What this changed

`docs/assumptions/crop-model.md`'s cross-check section was corrected to use this benchmark
instead of the miscited ~1/week figure, and a second summary field
(`steady_state_truss_rate_per_week`, `api/main.py`) was added to report the truss rate excluding
the ~55-day startup/ramp window that was diluting the original whole-season average.
