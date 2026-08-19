from twin.climate_model import ClimateState, GreenhouseClimateModel
from twin.params import CHPParams, ClimateControlParams, GeometryParams


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
        weak_state = weak_model.step(weak_state, hour=2, temp_out_c=cold_out_temp, solar_rad_w_m2=0.0, dt_hours=1.0).state
        strong_state = strong_model.step(strong_state, hour=2, temp_out_c=cold_out_temp, solar_rad_w_m2=0.0, dt_hours=1.0).state

    assert strong_state.temp_in_c > weak_state.temp_in_c


def test_ventilation_kicks_in_when_too_hot():
    geometry = _geometry()
    control = _control()
    chp = CHPParams(electric_power_kw=1000, heat_to_power_ratio=1.15, co2_kg_per_kwh_elec=0.18)
    model = GreenhouseClimateModel(geometry, chp, control)

    hot_state = ClimateState(temp_in_c=35.0, co2_in_ppm=420.0)
    result = model.step(hot_state, hour=13, temp_out_c=30.0, solar_rad_w_m2=800.0, dt_hours=1.0)

    assert result.vent_ach > control.vent_min_ach


def test_co2_injection_raises_concentration_above_ambient():
    geometry = _geometry()
    control = _control()
    chp = CHPParams(electric_power_kw=1000, heat_to_power_ratio=1.15, co2_kg_per_kwh_elec=0.18)
    model = GreenhouseClimateModel(geometry, chp, control)

    state = ClimateState(temp_in_c=20.0, co2_in_ppm=control.co2_ambient_ppm)
    for _ in range(6):
        state = model.step(state, hour=10, temp_out_c=15.0, solar_rad_w_m2=400.0, dt_hours=1.0).state

    assert state.co2_in_ppm > control.co2_ambient_ppm


def test_heat_available_and_co2_available_scale_with_fixed_electric_output():
    chp = CHPParams(electric_power_kw=1000, heat_to_power_ratio=1.15, co2_kg_per_kwh_elec=0.18)
    assert chp.heat_available_kw == 1150.0
    assert chp.co2_available_kg_per_hour == 180.0
