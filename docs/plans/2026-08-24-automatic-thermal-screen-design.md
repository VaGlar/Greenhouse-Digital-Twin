# Automatic thermal screen control + shading effect

**Status:** Approved 2026-08-24, ready for `writing-plans`.

## Background

The screen was previously deployed on a fixed clock schedule (`screen_open_hour`/`screen_close_hour`), user-adjustable in the frontend. Investigation (2026-08-24) showed that sweeping this schedule produces small, non-monotonic yield swings (~1-3% over a 150-day run) via an indirect temp→humidity→VPD→photosynthesis pathway on hours when the CHP isn't actively heating — not a coding bug, but confirmed the screen's real-world control logic is time-based *and* condition-based, and that the model was missing the screen's shading effect entirely (it only reduced transmission heat loss, never solar gain/light, despite the real product being a combined "55% shading / 55% energy saving" screen — `docs/papers/geothermiki-s192g-quote.md`).

The user described the real control logic: the screen closes at night, when it's very hot (shade), or when it's very cold and the CHP can't keep up (insulate, even at the cost of some lost sun) — and confirmed shading must now be modeled.

## Control logic

The screen becomes **fully automatic** — no user-facing schedule control. It deploys whenever any of these fire:

1. **Night** — outside `day_start_hour`/`day_end_hour` (the existing general day/night window, also used for heating/CO2 — no longer a separate screen-only clock).
2. **Too hot** — projected temperature (before ventilation) exceeds the *existing* ventilation threshold (`heating_setpoint(hour) + vent_temp_margin_c`). Shading only helps here (less solar gain reduces overheating), so no cost/benefit check needed.
3. **Cold + CHP insufficient, with a cost/benefit check** — when required heating power exceeds 90% of the CHP's fixed heat output (new `chp_heat_margin_fraction = 0.9`, **PLACEHOLDER**), compute the transmission-loss savings the screen would provide vs. the solar-gain loss from shading at that hour, and only deploy if the net effect actually helps (reduces the heat deficit). This directly addresses the case the user raised: on a cold-but-sunny hour, shading could lose more solar heat than the insulation saves.

Whenever deployed, the screen always applies **both** effects simultaneously (same physical fabric, same ~55% figure per the vendor spec for both shading and energy saving):
- Climate model: `q_trans_loss_w *= 1 - screen_energy_saving_fraction` (existing) and `q_solar_w *= 1 - screen_energy_saving_fraction` (new).
- Crop model: the solar radiation input to photosynthesis is reduced by the same factor whenever the screen is deployed for that hour, so lost light is a real yield cost, not just a climate-model side effect.

## Data flow / API changes

- `twin/params.py`: remove `screen_open_hour`/`screen_close_hour` (or keep internally as no-longer-configurable — TBD at implementation time, likely removed outright since the logic replaces them); add `chp_heat_margin_fraction: float = 0.9`. `ClimateControlParams` gains a method that returns the screen's deployed/retracted state for a given hour, given the current heat balance (needs `q_solar_w`, `q_trans_loss_w`, `required_w`, `heat_available_w` — computed in `twin/climate_model.py`, so the decision logic lives there, not as a pure `ClimateControlParams` method like the old `is_screen_deployed`).
- `twin/climate_model.py`: screen decision moves inline into `step()` where the energy balance is computed (needs `q_solar_w`/`q_trans_loss_w` before applying the screen, to run the cost/benefit check for the cold case). Screen state is returned in `ClimateStepResult` (new `screen_deployed: bool` field) so `twin/simulate.py` can pass it to the crop model.
- `twin/simulate.py`: passes `climate_result.screen_deployed` into `crop_model.step(...)` so shading reduces the solar input to photosynthesis for that hour.
- `twin/crop_model.py`: `step()` gains a `screen_deployed: bool` (or a pre-reduced `solar_rad_w_m2`) parameter; reduces effective light by `screen_energy_saving_fraction` when true.
- `api/main.py`: remove `screen_open_hour`/`screen_close_hour` from `SimulateRequest` (no longer user-configurable). Add to `daily_series`: `screen_closed_hours` (hours per day deployed). Add to `summary`: `screen_deployed_pct` (season average) and `heat_loss_avoided_kwh` (sum of the transmission-loss reduction actually realized while deployed, in kWh — a direct physical quantity, not a counterfactual second simulation).

## Frontend changes

- Remove the `screen_open_hour`/`screen_close_hour` sliders and their note entirely from the Υγρασία group.
- `GreenhouseSchematic`: replace the static `screenScheduleLabel` pin with a live one showing the season's `screen_deployed_pct` (e.g. "Κλειστή 58% του χρόνου") after a run; before a run, show a short static description that it operates automatically (night/heat/cold).
- New chart: "Ώρες κλειστής κουρτίνας/ημέρα" (`screen_closed_hours` from `daily_series`), styled with the existing `--humidity` token (same family as the screen's schematic zone).
- New stat tile or inline figure for `heat_loss_avoided_kwh` (energy saved by the screen) — placed near the existing "Θερμική κατανάλωση" stat tile.

## Documentation

- `docs/assumptions/climate-control.md`: rewrite the `screen_energy_saving_fraction` entry to describe the new automatic 3-criteria logic (replacing the `screen_open_hour`/`screen_close_hour` entry, which is removed) and to note the same 55% figure now governs shading too, per the vendor spec's own wording. Add a new entry for `chp_heat_margin_fraction` (0.9, PLACEHOLDER — a safety-margin choice, not literature-sourced).
- New `docs/papers/` citation card documenting the control-logic design decision itself (references this design doc + the vendor quote's "55% shading, ~55% energy saving" line already captured in `geothermiki-s192g-quote.md`).
- `docs/sources.xlsx` (was `docs/assumptions/sources.xlsx` at the time this plan was written): add the new `chp_heat_margin_fraction` row.
- `docs/plans/2026-08-21-greenhouse-schematic-frontend-design.md`'s zone table (screen → schedule sliders) is now stale for the screen row; update it to reflect the automatic behavior instead of user-adjustable hours.

## Testing

- `tests/test_climate_model.py`: new regression tests — screen deploys at night; screen deploys when projected temp exceeds the vent threshold (shading reduces solar gain for that hour); screen does NOT deploy for the cold-trigger when shading would lose more solar heat than insulation saves (constructed scenario); screen DOES deploy for the cold-trigger when insulation net-helps.
- `tests/test_crop_model.py`: new test confirming shaded solar input reduces gross assimilation by the expected factor when `screen_deployed=True`.

## Out of scope

- No second "counterfactual" simulation run to compute a precise "yield lost to shading" figure — `heat_loss_avoided_kwh` is an analytical estimate from the realized transmission-loss reduction, not a full without-screen comparison.
- No user control over any of the three thresholds (night window aside, which stays tied to the existing `day_start_hour`/`day_end_hour`) in this pass.
