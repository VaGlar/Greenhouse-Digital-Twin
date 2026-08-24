# Automatic thermal screen control logic — design decision, not a literature source

- **Type:** User-specified control logic + engineering derivation (not a published source)
- **Retrieved:** 2026-08-24, from direct conversation with the user
- **Used for:** `screen_energy_saving_fraction` (deployment logic), `chp_heat_margin_fraction`, `VENT_RAMP_BAND_C` reuse (twin/climate_model.py)

## What this documents

The thermal screen's deployment logic (`GreenhouseClimateModel.decide_screen_deployment`) is not from a paper — it's a direct translation of how the user (who has practical greenhouse operating knowledge) described a real screen controller behaving, refined through several rounds of the user pointing out consequences the initial version got wrong:

> "η κουρτίνα κλείνει όταν: είναι νύχτα ή όταν έχει πολλή ζέστη. Όταν έχει πολύ κρύο και δεν αρκεί η θέρμανση από την CHP, μήπως πρέπει να κλείνει και η κουρτίνα κι ας χάνουμε και λίγο ήλιο; Σίγουρα πρέπει να λάβουμε υπόψη τη σκίαση."
>
> ("The screen closes when: it's night, or when it's very hot. When it's very cold and CHP heating isn't enough, shouldn't the screen close too, even losing some sun? We definitely need to account for shading.")

The user then flagged, unprompted, that closing the screen also shades the greenhouse — changing its solar heat gain, not just its heat loss — which is what led to the cost/benefit check on the cold trigger (rather than a naive "close whenever cold" rule) and, separately, to the design doc's approved 3-criteria structure (`docs/plans/2026-08-24-automatic-thermal-screen-design.md`).

## Two numeric choices made during implementation, not from a source

- **`chp_heat_margin_fraction = 0.9`**: the user picked 90% directly when asked (vs. waiting for 100%, which would mean the setpoint is already being missed) — an operational judgment call, not sourced.
- **"Too hot" threshold**: initially set equal to `vent_setpoint` (where ventilation starts ramping), per the user's approval of that option during design. Empirically found (2026-08-24, this implementation) to shade ~59% of all daytime hours and cut yield ~17% for no real benefit — actual indoor temperature never exceeded ~25°C either way, since ventilation alone was already handling the load. Corrected to `vent_setpoint + VENT_RAMP_BAND_C` (the point ventilation is *fully* ramped, not merely starting) — this reduced daytime shading to ~29% of hours and restored yield to ~15.5 kg/m², matching the old fixed night-only schedule.
