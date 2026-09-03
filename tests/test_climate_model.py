import pytest

from twin.climate_model import ClimateState, GreenhouseClimateModel
from twin.params import CHPParams, ClimateControlParams, ClimatePhase, GeometryParams


def _geometry() -> GeometryParams:
    return GeometryParams(area_m2=5000, height_m=5.5, cover_u_value_w_m2k=6.0, cover_transmissivity=0.7)


def _control() -> ClimateControlParams:
    return ClimateControlParams(heating_setpoint_day_c=20.0, heating_setpoint_night_c=17.0)


def test_more_chp_heat_raises_steady_state_temperature():
    geometry = _geometry()
    control = _control()

    weak_chp = CHPParams(electric_power_kw=1000, heat_to_power_ratio=0.05, co2_kg_per_kwh_elec=0.18)
    strong_chp = CHPParams(electric_power_kw=1000, heat_to_power_ratio=2.0, co2_kg_per_kwh_elec=0.18)

    cold_out_temp = -5.0
    state = ClimateState(temp_in_c=5.0, co2_in_ppm=420.0)

    weak_model = GreenhouseClimateModel(geometry, weak_chp, control)
    strong_model = GreenhouseClimateModel(geometry, strong_chp, control)

    weak_state = state
    strong_state = state
    for _ in range(48):
        weak_state = weak_model.step(weak_state, hour=2, temp_out_c=cold_out_temp, solar_rad_w_m2=0.0, dt_hours=1.0, phase=ClimatePhase.VEGETATIVE).state
        strong_state = strong_model.step(strong_state, hour=2, temp_out_c=cold_out_temp, solar_rad_w_m2=0.0, dt_hours=1.0, phase=ClimatePhase.VEGETATIVE).state

    assert strong_state.temp_in_c > weak_state.temp_in_c


def test_ventilation_kicks_in_when_too_hot():
    geometry = _geometry()
    control = _control()
    chp = CHPParams(electric_power_kw=1000, heat_to_power_ratio=1.15, co2_kg_per_kwh_elec=0.18)
    model = GreenhouseClimateModel(geometry, chp, control)

    hot_state = ClimateState(temp_in_c=35.0, co2_in_ppm=420.0)
    result = model.step(hot_state, hour=13, temp_out_c=30.0, solar_rad_w_m2=800.0, dt_hours=1.0, phase=ClimatePhase.VEGETATIVE)

    assert result.vent_ach > control.vent_min_ach


def test_co2_injection_raises_concentration_above_ambient():
    geometry = _geometry()
    control = _control()
    chp = CHPParams(electric_power_kw=1000, heat_to_power_ratio=1.15, co2_kg_per_kwh_elec=0.18)
    model = GreenhouseClimateModel(geometry, chp, control)

    state = ClimateState(temp_in_c=20.0, co2_in_ppm=control.co2_ambient_ppm)
    for _ in range(6):
        state = model.step(state, hour=10, temp_out_c=15.0, solar_rad_w_m2=400.0, dt_hours=1.0, phase=ClimatePhase.VEGETATIVE).state

    assert state.co2_in_ppm > control.co2_ambient_ppm


def test_heat_available_and_co2_available_scale_with_fixed_electric_output():
    chp = CHPParams(electric_power_kw=1000, heat_to_power_ratio=1.15, co2_kg_per_kwh_elec=0.18)
    assert chp.heat_available_kw == 1150.0
    assert chp.co2_available_kg_per_hour == 180.0


def test_dry_ventilation_lowers_humidity_toward_outdoor():
    geometry = _geometry()
    control = _control()
    chp = CHPParams(electric_power_kw=1000, heat_to_power_ratio=1.15, co2_kg_per_kwh_elec=0.18)
    model = GreenhouseClimateModel(geometry, chp, control)

    humid_state = ClimateState(temp_in_c=25.0, co2_in_ppm=420.0, vapor_pressure_kpa=2.5)
    # hot enough to force strong ventilation, dry outdoor air
    result = model.step(humid_state, hour=13, temp_out_c=25.0, solar_rad_w_m2=800.0, dt_hours=1.0, phase=ClimatePhase.VEGETATIVE, rh_out_pct=20.0)

    assert result.state.vapor_pressure_kpa < humid_state.vapor_pressure_kpa


def test_cold_cover_condenses_moisture_out_of_humid_air():
    geometry = _geometry()
    control = _control()
    chp = CHPParams(electric_power_kw=1000, heat_to_power_ratio=1.15, co2_kg_per_kwh_elec=0.18)
    model = GreenhouseClimateModel(geometry, chp, control)

    # warm, humid interior air; very cold outside -> cold cover surface, forces condensation
    # even though the ventilation rate is at its minimum (not itself removing much moisture)
    humid_state = ClimateState(temp_in_c=20.0, co2_in_ppm=420.0, vapor_pressure_kpa=2.0)
    result = model.step(humid_state, hour=2, temp_out_c=-10.0, solar_rad_w_m2=0.0, dt_hours=1.0, phase=ClimatePhase.VEGETATIVE, rh_out_pct=80.0)

    assert result.condensed_kg > 0.0


def test_ventilation_does_not_overshoot_below_vent_setpoint_on_cold_sunny_days():
    geometry = _geometry()
    control = _control()
    chp = CHPParams(electric_power_kw=1000, heat_to_power_ratio=1.15, co2_kg_per_kwh_elec=0.18)
    model = GreenhouseClimateModel(geometry, chp, control)

    # Cold outside but strong sun -- pushes indoor well above vent_setpoint, forcing max-ramp
    # ventilation. Bug (fixed 2026-08-25): the naive linear removal crashed indoor air all the
    # way down to outdoor temperature instead of stopping at vent_setpoint.
    hot_state = ClimateState(temp_in_c=20.0, co2_in_ppm=420.0)
    result = model.step(hot_state, hour=11, temp_out_c=-5.0, solar_rad_w_m2=900.0, dt_hours=1.0, phase=ClimatePhase.VEGETATIVE)

    vent_setpoint = control.heating_setpoint_day_c + control.vent_temp_margin_c
    assert result.state.temp_in_c == vent_setpoint
    assert result.state.temp_in_c > -5.0  # must not have crashed toward outdoor air


def test_ventilation_still_floors_at_outdoor_air_on_a_genuinely_hot_day():
    geometry = _geometry()
    control = _control()
    chp = CHPParams(electric_power_kw=1000, heat_to_power_ratio=1.15, co2_kg_per_kwh_elec=0.18)
    model = GreenhouseClimateModel(geometry, chp, control)

    # Outdoor air itself is already above vent_setpoint -- ventilation legitimately can't cool
    # below ambient, this is not the overshoot bug, so the floor should be outdoor temp here.
    hot_state = ClimateState(temp_in_c=30.0, co2_in_ppm=420.0)
    result = model.step(hot_state, hour=13, temp_out_c=25.0, solar_rad_w_m2=800.0, dt_hours=1.0, phase=ClimatePhase.VEGETATIVE)

    assert result.state.temp_in_c >= 25.0


def test_screen_deploys_at_night_regardless_of_conditions():
    geometry = _geometry()
    control = _control()
    chp = CHPParams(electric_power_kw=1000, heat_to_power_ratio=1.15, co2_kg_per_kwh_elec=0.18)
    model = GreenhouseClimateModel(geometry, chp, control)

    state = ClimateState(temp_in_c=17.0, co2_in_ppm=420.0)
    # hour=2 is night (default day window 6-20); mild conditions, no other trigger would fire
    assert model.decide_screen_deployment(state, hour=2, temp_out_c=10.0, solar_rad_w_m2=0.0, dt_hours=1.0, phase=ClimatePhase.VEGETATIVE) is True


def test_screen_deploys_for_shading_when_ventilation_alone_would_not_be_enough():
    geometry = _geometry()
    control = _control()
    chp = CHPParams(electric_power_kw=1000, heat_to_power_ratio=1.15, co2_kg_per_kwh_elec=0.18)
    model = GreenhouseClimateModel(geometry, chp, control)

    # scorching midday sun, already-hot indoor air -- even max ventilation can't hold this
    state = ClimateState(temp_in_c=30.0, co2_in_ppm=420.0)
    assert model.decide_screen_deployment(state, hour=13, temp_out_c=35.0, solar_rad_w_m2=900.0, dt_hours=1.0, phase=ClimatePhase.VEGETATIVE) is True


def test_screen_deploys_for_cold_when_chp_insufficient_and_no_sun_to_lose():
    geometry = _geometry()
    control = _control()
    # weak CHP -- easily overwhelmed by a cold night/overcast day
    weak_chp = CHPParams(electric_power_kw=1000, heat_to_power_ratio=0.05, co2_kg_per_kwh_elec=0.18)
    model = GreenhouseClimateModel(geometry, weak_chp, control)

    # daytime hour so this exercises the cold-trigger branch specifically (not the night one),
    # but overcast (no solar) -- insulating has nothing but upside here
    state = ClimateState(temp_in_c=5.0, co2_in_ppm=420.0)
    assert model.decide_screen_deployment(state, hour=13, temp_out_c=-10.0, solar_rad_w_m2=0.0, dt_hours=1.0, phase=ClimatePhase.VEGETATIVE) is True


def test_screen_stays_retracted_when_cold_but_sun_outweighs_insulation_benefit():
    geometry = _geometry()
    control = _control()
    # same weak CHP as above -- still can't keep up with the cold on its own
    weak_chp = CHPParams(electric_power_kw=1000, heat_to_power_ratio=0.05, co2_kg_per_kwh_elec=0.18)
    model = GreenhouseClimateModel(geometry, weak_chp, control)

    # cold outside, but real winter sun -- the screen would block more free solar heat than
    # its insulation would save, so a real controller (and this one) should leave it open
    state = ClimateState(temp_in_c=5.0, co2_in_ppm=420.0)
    assert model.decide_screen_deployment(state, hour=13, temp_out_c=-10.0, solar_rad_w_m2=200.0, dt_hours=1.0, phase=ClimatePhase.VEGETATIVE) is False


def test_fan_pad_cooling_pulls_temperature_below_raw_outdoor_air():
    geometry = _geometry()
    chp = CHPParams(electric_power_kw=1000, heat_to_power_ratio=1.15, co2_kg_per_kwh_elec=0.18)

    no_pad_control = _control()
    pad_control = ClimateControlParams(
        heating_setpoint_day_c=20.0,
        heating_setpoint_night_c=17.0,
        fan_pad_cooling_enabled=True,
        fan_pad_efficiency=0.80,
    )

    # Hot, dry midday -- low RH means a big dry-bulb/wet-bulb gap, so pads have real
    # cooling potential; active (above-baseline) ventilation is engaged either way.
    hot_state = ClimateState(temp_in_c=32.0, co2_in_ppm=420.0)
    no_pad_result = GreenhouseClimateModel(geometry, chp, no_pad_control).step(
        hot_state, hour=13, temp_out_c=32.0, solar_rad_w_m2=800.0, dt_hours=1.0, phase=ClimatePhase.VEGETATIVE, rh_out_pct=25.0
    )
    pad_result = GreenhouseClimateModel(geometry, chp, pad_control).step(
        hot_state, hour=13, temp_out_c=32.0, solar_rad_w_m2=800.0, dt_hours=1.0, phase=ClimatePhase.VEGETATIVE, rh_out_pct=25.0
    )

    assert pad_result.state.temp_in_c < no_pad_result.state.temp_in_c


def test_fan_pad_cooling_also_raises_humidity_brought_in_by_ventilation():
    geometry = _geometry()
    chp = CHPParams(electric_power_kw=1000, heat_to_power_ratio=1.15, co2_kg_per_kwh_elec=0.18)

    no_pad_control = _control()
    pad_control = ClimateControlParams(
        heating_setpoint_day_c=20.0,
        heating_setpoint_night_c=17.0,
        fan_pad_cooling_enabled=True,
        fan_pad_efficiency=0.80,
    )

    # Same dry, hot, actively-ventilated scenario -- pad-cooled air is necessarily also
    # pad-humidified (adiabatic process), so vapor pressure should end up higher than
    # ventilating with raw dry outdoor air.
    dry_state = ClimateState(temp_in_c=32.0, co2_in_ppm=420.0, vapor_pressure_kpa=1.0)
    no_pad_result = GreenhouseClimateModel(geometry, chp, no_pad_control).step(
        dry_state, hour=13, temp_out_c=32.0, solar_rad_w_m2=800.0, dt_hours=1.0, phase=ClimatePhase.VEGETATIVE, rh_out_pct=25.0
    )
    pad_result = GreenhouseClimateModel(geometry, chp, pad_control).step(
        dry_state, hour=13, temp_out_c=32.0, solar_rad_w_m2=800.0, dt_hours=1.0, phase=ClimatePhase.VEGETATIVE, rh_out_pct=25.0
    )

    assert pad_result.state.vapor_pressure_kpa > no_pad_result.state.vapor_pressure_kpa


def test_fan_pad_cooling_disengaged_when_toggle_is_off_even_if_efficiency_is_set():
    geometry = _geometry()
    control = ClimateControlParams(
        heating_setpoint_day_c=20.0,
        heating_setpoint_night_c=17.0,
        fan_pad_cooling_enabled=False,
        fan_pad_efficiency=0.80,
    )
    chp = CHPParams(electric_power_kw=1000, heat_to_power_ratio=1.15, co2_kg_per_kwh_elec=0.18)
    model = GreenhouseClimateModel(geometry, chp, control)

    temp_c, vapor_kpa = model._fan_pad_outdoor_conditions(temp_out_c=32.0, rh_out_pct=25.0)
    assert temp_c == 32.0


def test_fan_pad_active_flag_is_true_when_engaged():
    geometry = _geometry()
    chp = CHPParams(electric_power_kw=1000, heat_to_power_ratio=1.15, co2_kg_per_kwh_elec=0.18)
    pad_control = ClimateControlParams(
        heating_setpoint_day_c=20.0,
        heating_setpoint_night_c=17.0,
        fan_pad_cooling_enabled=True,
        fan_pad_efficiency=0.80,
    )
    hot_state = ClimateState(temp_in_c=32.0, co2_in_ppm=420.0)
    result = GreenhouseClimateModel(geometry, chp, pad_control).step(
        hot_state, hour=13, temp_out_c=32.0, solar_rad_w_m2=800.0, dt_hours=1.0, phase=ClimatePhase.VEGETATIVE, rh_out_pct=25.0
    )
    assert result.fan_pad_active is True


def test_fan_pad_active_flag_is_false_when_toggle_is_off():
    geometry = _geometry()
    chp = CHPParams(electric_power_kw=1000, heat_to_power_ratio=1.15, co2_kg_per_kwh_elec=0.18)
    no_pad_control = _control()
    hot_state = ClimateState(temp_in_c=32.0, co2_in_ppm=420.0)
    result = GreenhouseClimateModel(geometry, chp, no_pad_control).step(
        hot_state, hour=13, temp_out_c=32.0, solar_rad_w_m2=800.0, dt_hours=1.0, phase=ClimatePhase.VEGETATIVE, rh_out_pct=25.0
    )
    assert result.fan_pad_active is False


def test_fan_pad_active_flag_is_false_during_passive_baseline_ventilation():
    geometry = _geometry()
    chp = CHPParams(electric_power_kw=1000, heat_to_power_ratio=1.15, co2_kg_per_kwh_elec=0.18)
    pad_control = ClimateControlParams(
        heating_setpoint_day_c=20.0,
        heating_setpoint_night_c=17.0,
        fan_pad_cooling_enabled=True,
        fan_pad_efficiency=0.80,
    )
    # Cool night, well under the vent setpoint -- ventilation stays at the passive
    # baseline (vent_min_ach), so the pads should not be reported as engaged.
    cool_state = ClimateState(temp_in_c=17.0, co2_in_ppm=420.0)
    result = GreenhouseClimateModel(geometry, chp, pad_control).step(
        cool_state, hour=2, temp_out_c=10.0, solar_rad_w_m2=0.0, dt_hours=1.0, phase=ClimatePhase.VEGETATIVE, rh_out_pct=70.0
    )
    assert result.fan_pad_active is False


def test_active_dehumidification_caps_relative_humidity_at_setpoint():
    # Demand comfortably within the default (~771 kg/hour) capacity -- reaches the setpoint.
    geometry = _geometry()
    control = _control()  # dehumidification_setpoint_pct defaults to 70.0
    chp = CHPParams(electric_power_kw=1000, heat_to_power_ratio=1.15, co2_kg_per_kwh_elec=0.18)
    model = GreenhouseClimateModel(geometry, chp, control)

    # push vapor pressure near saturation; humid, still outdoor air (little ventilation relief)
    saturated_state = ClimateState(temp_in_c=20.0, co2_in_ppm=420.0, vapor_pressure_kpa=2.3)
    result = model.step(saturated_state, hour=2, temp_out_c=18.0, solar_rad_w_m2=0.0, dt_hours=1.0, phase=ClimatePhase.VEGETATIVE, rh_out_pct=95.0)

    assert result.rh_in_pct <= control.dehumidification_setpoint_pct + 0.01
    assert result.dehumidified_kg > 0.0
    assert result.dehumidified_kg < control.dehumidification_capacity_kg_water_per_hour


def test_dehumidification_is_capped_by_real_capacity_under_extreme_demand():
    # Bug fix 2026-08-25: active dehumidification used to be unconstrained (always assumed
    # sufficient to reach the setpoint within the hour). Under demand that exceeds the real
    # removal capacity, the setpoint should NOT be fully reached -- the RH ceiling from
    # earlier is now a target, not a guarantee. Uses an explicitly small capacity here (rather
    # than the ~771 kg/hour default, sized for a real 5000 m2 semi-closed system, which a
    # single hour's demand in this small test fixture can't realistically exceed) to isolate
    # the capping behavior itself.
    geometry = _geometry()
    control = ClimateControlParams(
        heating_setpoint_day_c=20.0,
        heating_setpoint_night_c=17.0,
        dehumidification_capacity_kg_water_per_hour=50.0,
    )
    chp = CHPParams(electric_power_kw=1000, heat_to_power_ratio=1.15, co2_kg_per_kwh_elec=0.18)
    model = GreenhouseClimateModel(geometry, chp, control)

    saturated_state = ClimateState(temp_in_c=20.0, co2_in_ppm=420.0, vapor_pressure_kpa=2.3)
    result = model.step(saturated_state, hour=2, temp_out_c=18.0, solar_rad_w_m2=0.0, dt_hours=1.0, phase=ClimatePhase.VEGETATIVE, rh_out_pct=95.0)

    assert result.dehumidified_kg == pytest.approx(control.dehumidification_capacity_kg_water_per_hour, rel=1e-6)
    assert result.rh_in_pct > control.dehumidification_setpoint_pct + 0.01


# -- Phase-aware climate control, temperature (docs/plans/2026-08-31-phase-aware-climate-design.md) --


def test_full_fruiting_phase_reaches_a_higher_steady_state_temperature_than_vegetative():
    geometry = _geometry()
    control = ClimateControlParams(
        heating_setpoint_day_c=20.0,
        heating_setpoint_night_c=17.0,
        full_fruiting_heating_setpoint_day_delta_c=3.0,
        full_fruiting_heating_setpoint_night_delta_c=3.0,
    )
    chp = CHPParams(electric_power_kw=1000, heat_to_power_ratio=2.0, co2_kg_per_kwh_elec=0.18)

    cold_out_temp = -5.0
    state = ClimateState(temp_in_c=5.0, co2_in_ppm=420.0)

    vegetative_model = GreenhouseClimateModel(geometry, chp, control)
    full_fruiting_model = GreenhouseClimateModel(geometry, chp, control)

    vegetative_state = state
    full_fruiting_state = state
    for _ in range(48):
        vegetative_state = vegetative_model.step(
            vegetative_state, hour=2, temp_out_c=cold_out_temp, solar_rad_w_m2=0.0, dt_hours=1.0, phase=ClimatePhase.VEGETATIVE
        ).state
        full_fruiting_state = full_fruiting_model.step(
            full_fruiting_state, hour=2, temp_out_c=cold_out_temp, solar_rad_w_m2=0.0, dt_hours=1.0, phase=ClimatePhase.FULL_FRUITING
        ).state

    assert full_fruiting_state.temp_in_c > vegetative_state.temp_in_c
