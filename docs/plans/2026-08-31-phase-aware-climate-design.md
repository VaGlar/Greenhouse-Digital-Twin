# Phase-aware climate control (temperature, first pass)

**Status:** Approved 2026-08-31, ready for `writing-plans`.

## Background

`climate_control` setpoints (heating day/night, CO2 day setpoint, dehumidification RH setpoint)
are flat constants for the whole `duration_days` run. Real growers change climate strategy as
the crop matures — a different day/night temperature target during vegetative growth than during
full fruiting, for example. The crop model already has phase boundaries
(`CropParams.fruiting_start_days`, `fruiting_ramp_days`) used for reporting
(`summary.steady_state_truss_rate_per_week`, `full_production_start_day`) but nothing in
`climate_control` reads them. Agreed with the user 2026-08-26 as the next roadmap item after
hydroponics Level A/B (completed 2026-08-29).

Scoped for this pass (2026-08-31): **temperature only** (heating day/night setpoints). CO2 and
dehumidification RH phase-awareness are explicitly deferred — see "Out of scope" — but the
pattern established here is meant to extend directly to them later.

## Phases (reuse the existing crop-model boundary, no new boundary config)

- **Vegetative**: `days_after_planting < fruiting_start_days`
- **Ramp-up**: `fruiting_start_days <= days_after_planting < fruiting_start_days + fruiting_ramp_days`
- **Full fruiting**: `days_after_planting >= fruiting_start_days + fruiting_ramp_days`

New `ClimatePhase` enum (`VEGETATIVE`, `RAMP_UP`, `FULL_FRUITING`) and a pure function
`crop_growth_phase(days_after_planting: float, crop: CropParams) -> ClimatePhase` in
`twin/crop_model.py`, next to the existing phase-boundary logic
(`_fruit_partition_fraction`).

## Setpoint design: baseline + relative deltas (not three parallel setpoint sets)

Considered and rejected a nested `ClimatePhaseSetpoints` dataclass with three parallel instances
(`vegetative`/`ramp_up`/`full_fruiting`) — cleaner-looking in isolation, but it would require
reworking the `/simulate` override semantics and the frontend sliders to decide which phase(s) a
single slider drag should affect.

Chosen instead: the existing `heating_setpoint_day_c` / `heating_setpoint_night_c` fields keep
their exact current meaning (now explicitly *the vegetative-phase target*). Four new fields hold
each later phase's *delta* from that baseline:

- `ramp_up_heating_setpoint_day_delta_c: float = 0.0`
- `ramp_up_heating_setpoint_night_delta_c: float = 0.0`
- `full_fruiting_heating_setpoint_day_delta_c: float = 0.0`
- `full_fruiting_heating_setpoint_night_delta_c: float = 0.0`

All four default to **0.0 (PLACEHOLDER)** — zero behavior change until real magnitudes are
researched and set at implementation time, same pattern as every other Level A/B field that
started at a documented placeholder. A phase's effective target = baseline + that phase's delta
(vegetative delta is always 0 by construction).

This means the existing `/simulate` `heating_setpoint_day_c`/`heating_setpoint_night_c` overrides
and the existing frontend sliders need **no changes at all** — overriding the baseline
automatically shifts all three phases by the same amount, which is exactly the "one slider =
offset for every phase" behavior already agreed with the user, achieved structurally rather than
by special-casing the override logic.

## `twin/params.py`

- `ClimateControlParams.heating_setpoint(hour: int, phase: ClimatePhase) -> float` — gains the
  `phase` parameter (was `heating_setpoint(hour)`). Returns the day/night base (existing
  `is_daytime(hour)` logic, unchanged) plus that phase's delta (0.0 for vegetative).
- New validation: the four delta fields must be finite floats (no other constraint — a negative
  delta, e.g. cooler ramp-up nights, is valid).

## `twin/climate_model.py` / `twin/simulate.py`

- Both existing call sites of `self.control.heating_setpoint(hour)` (`decide_screen_deployment`
  and `step()`) gain a `phase: ClimatePhase` parameter, threaded through from their callers.
- `twin/simulate.py`: compute `phase = crop_growth_phase(crop_state.days_after_planting,
  params.crop)` once per hour (before the crop model advances `crop_state` for that hour, same
  ordering as the existing `temp_in_c`/`co2_in_ppm` reads — climate for hour N sees crop state as
  of the start of hour N) and pass it into both `climate_model` calls for that hour.

## API / frontend

- `daily_series` gains a `climate_phase` string field (`"vegetative"` / `"ramp_up"` /
  `"full_fruiting"`) — informational, derived the same way as other reporting-layer fields.
  **Update (same day, user follow-up)**: surfaced as a small badge in the `DayScrubber` next to
  the viewed day's date, so the viewed phase is visible without cross-referencing the config —
  this was originally scoped as "no UI yet", but doing it turned out to be a few-line addition
  once the field already existed, so it shipped in the same pass instead of staying deferred.
- No changes to `SimulateRequest`, `_apply_overrides`, or any frontend slider — see "Setpoint
  design" above for why.

## Documentation

- `docs/assumptions/climate-control.md`: new entries for the four delta fields (PLACEHOLDER,
  0.0 default), and a short note that `heating_setpoint_day_c`/`heating_setpoint_night_c` are now
  explicitly the vegetative-phase target (previously the single flat value for the whole season).
- `docs/assumptions/README.md` and `README.md`: update the phase-aware bullet from "planned next"
  to describe this scoped first pass (temperature only; CO2/RH still open).
- `docs/sources.xlsx`: add rows for the four new delta fields (PLACEHOLDER).

## Testing

- `tests/test_params.py`: `heating_setpoint(hour, phase)` returns the baseline for
  `ClimatePhase.VEGETATIVE` regardless of delta fields; returns `baseline + delta` for
  `RAMP_UP`/`FULL_FRUITING` when deltas are configured non-zero; rejects non-finite deltas.
- `tests/test_crop_model.py` (or a new small test near `_fruit_partition_fraction`'s tests):
  `crop_growth_phase()` returns the correct phase at the two boundaries and just inside/outside
  each of the three ranges.
- `tests/test_climate_model.py`: a scenario with non-zero deltas produces a different heating
  target when `phase` changes, all else equal.
- `tests/test_simulation_regression.py` or `tests/test_api.py`: a full run's `daily_series`
  transitions `climate_phase` at the expected `days_after_planting` boundaries (using the
  default `fruiting_start_days`/`fruiting_ramp_days`).
- `tests/test_api.py`: overriding the baseline `heating_setpoint_day_c` shifts the realized
  indoor temperature by roughly the same amount in every phase (confirms the "one slider, all
  phases" behavior holds end-to-end, not just at the `ClimateControlParams` unit level).

## Out of scope (this pass)

- **CO2 setpoint and dehumidification RH phase-awareness** — deferred; the baseline+delta field
  pattern established here is meant to extend directly to them (e.g.
  `full_fruiting_co2_setpoint_day_delta_ppm`) when that work starts.
- **Real literature-sourced delta magnitudes** — researched at implementation time (short web
  search, same methodology as hydroponics Level A/B); defaults start at 0.0 so there is no
  behavior change in `config/greenhouse_example.yaml`'s current run until real values are chosen
  and set.
- **Per-phase UI sliders** — deferred per the user's explicit choice; one slider continues to
  control all three phases via the baseline+delta structure.
- **Smooth/gradual interpolation between phases** — deltas apply as a discrete step exactly at
  the phase boundary, consistent with how other discrete triggers already work in this model
  (screen deployment, BER threshold).
