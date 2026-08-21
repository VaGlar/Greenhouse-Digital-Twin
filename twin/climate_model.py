"""Single-zone greenhouse climate model (GreenLight-lite).

Simplified hourly energy and CO2 mass balance for the greenhouse air.
Not a faithful port of the Wageningen GreenLight model — a deliberately
smaller model inspired by its structure (solar gain, transmission loss,
ventilation, CHP heat/CO2 supply), sized for an MVP that is easy to
understand, test, and later recalibrate against real sensor data.

Key modeling choice (confirmed by the user): the CHP unit's electrical
output is FIXED (grid-driven, not greenhouse-driven), so its heat and CO2
output are also fixed. The greenhouse draws what it needs from that fixed
supply; the rest is dumped (excess heat) or vented (excess CO2) — the CHP
itself is never modulated based on greenhouse demand.

Thermal screen: deployed every night (retracted during the day), cutting
transmission heat loss by a fixed fraction. Modeled as a simple day/night
toggle, not a continuous deploy/retract control loop.

Humidity: tracked as vapor pressure (kPa), the same way real greenhouse
models do (rather than tracking relative humidity directly, which is
nonlinear in temperature). Water enters the air from crop transpiration
(computed in twin/crop_model.py) and leaves via ventilation exchange with
outdoor air -- the same ventilation rate already computed for the energy
balance. No condensation/dehumidification is modeled: vapor pressure is
simply capped at saturation (100% RH), so excess moisture is implicitly
"lost" rather than physically tracked as condensate on the cover.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from twin.params import CHPParams, ClimateControlParams, GeometryParams

AIR_VOLUMETRIC_HEAT_CAPACITY_J_M3K = 1_200.0  # ~ air density (1.2 kg/m3) x specific heat (1005 J/kgK)
CO2_DENSITY_KG_M3 = 1.83  # density of CO2 gas at ~20C, used only to convert mass <-> ppm
WATER_MOLAR_MASS_G_MOL = 18.02  # physical constant
GAS_CONSTANT_J_MOL_K = 8.314  # physical constant (ideal gas law)


def _saturation_vapor_pressure_kpa(temp_c: float) -> float:
    """Tetens/Magnus formula, kPa. Standard meteorological equation (e.g. FAO-56
    Penman-Monteith reference, Allen et al. 1998, eq. 11) -- not a model assumption."""
    return 0.6108 * math.exp(17.27 * temp_c / (temp_c + 237.3))


@dataclass
class ClimateState:
    temp_in_c: float
    co2_in_ppm: float
    vapor_pressure_kpa: float = 1.0  # ~65% RH at 20C; overwritten by the first step anyway


@dataclass
class ClimateStepResult:
    state: ClimateState
    heat_used_kw: float
    heat_dumped_kw: float
    vent_ach: float
    co2_injected_kg: float
    co2_dumped_kg: float
    rh_in_pct: float
    vpd_kpa: float


class GreenhouseClimateModel:
    def __init__(self, geometry: GeometryParams, chp: CHPParams, control: ClimateControlParams):
        self.geometry = geometry
        self.chp = chp
        self.control = control
        self._thermal_capacity_j_k = control.effective_heat_capacity_j_m2k * geometry.area_m2

    def step(
        self,
        state: ClimateState,
        hour: int,
        temp_out_c: float,
        solar_rad_w_m2: float,
        dt_hours: float,
        co2_uptake_kg_per_hour: float = 0.0,
        rh_out_pct: float = 60.0,
        transpiration_kg_per_hour: float = 0.0,
    ) -> ClimateStepResult:
        dt_s = dt_hours * 3600.0
        c_total = self._thermal_capacity_j_k

        # --- Energy balance: solar gain vs. transmission loss ---
        q_solar_w = solar_rad_w_m2 * self.geometry.area_m2 * self.geometry.cover_transmissivity
        q_trans_loss_w = self.geometry.cover_u_value_w_m2k * self.geometry.cover_area_m2 * (state.temp_in_c - temp_out_c)
        # Thermal screen: deployed at night only (retracted during the day so it doesn't block
        # light) -- cuts transmission heat loss by its rated energy-saving fraction.
        if not self.control.is_daytime(hour):
            q_trans_loss_w *= 1.0 - self.control.screen_energy_saving_fraction
        net_w = q_solar_w - q_trans_loss_w
        temp_pred = state.temp_in_c + net_w * dt_s / c_total

        # --- Heating from the CHP's fixed, constant heat supply ---
        setpoint = self.control.heating_setpoint(hour)
        heat_available_w = self.chp.heat_available_kw * 1000.0
        if temp_pred < setpoint:
            required_w = (setpoint - temp_pred) * c_total / dt_s
            heat_used_w = min(required_w, heat_available_w)
        else:
            heat_used_w = 0.0
        temp_after_heat = temp_pred + heat_used_w * dt_s / c_total
        heat_used_kw = heat_used_w / 1000.0
        heat_dumped_kw = self.chp.heat_available_kw - heat_used_kw

        # --- Ventilation: ramps up once temperature exceeds setpoint + margin ---
        vent_setpoint = setpoint + self.control.vent_temp_margin_c
        excess = max(0.0, temp_after_heat - vent_setpoint)
        ramp_band_c = 5.0
        ramp_fraction = min(1.0, excess / ramp_band_c)
        ach = self.control.vent_min_ach + (self.control.vent_max_ach - self.control.vent_min_ach) * ramp_fraction

        delta_t = temp_after_heat - temp_out_c
        vent_removal_w = ach * self.geometry.volume_m3 * AIR_VOLUMETRIC_HEAT_CAPACITY_J_M3K / 3600.0 * delta_t
        temp_new = temp_after_heat - vent_removal_w * dt_s / c_total
        if delta_t > 0:
            temp_new = max(temp_new, temp_out_c)  # ventilation can't cool below outside air

        # --- CO2 balance: fixed CHP output, but dosing is capped at the
        # setpoint (like a real CO2 dosing controller) — the rest of the
        # CHP's constant flue-gas CO2 output bypasses straight to atmosphere
        # rather than being pumped into the greenhouse and vented back out.
        co2_after_vent = self.control.co2_ambient_ppm + (state.co2_in_ppm - self.control.co2_ambient_ppm) * math.exp(
            -ach * dt_hours
        )
        delta_ppm_uptake = co2_uptake_kg_per_hour * dt_hours / CO2_DENSITY_KG_M3 / self.geometry.volume_m3 * 1e6
        co2_before_dosing = max(200.0, co2_after_vent - delta_ppm_uptake)

        co2_target_ppm = self.control.co2_setpoint_day_ppm if self.control.is_daytime(hour) else self.control.co2_ambient_ppm
        available_kg = self.chp.co2_available_kg_per_hour * dt_hours
        required_ppm = max(0.0, co2_target_ppm - co2_before_dosing)
        required_kg = required_ppm * CO2_DENSITY_KG_M3 * self.geometry.volume_m3 / 1e6
        injected_kg = min(available_kg, required_kg)
        co2_dumped_kg = available_kg - injected_kg

        delta_ppm_injection = injected_kg / CO2_DENSITY_KG_M3 / self.geometry.volume_m3 * 1e6
        co2_new = max(co2_before_dosing + delta_ppm_injection, 200.0)

        # --- Humidity balance: ventilation exchange (same ach as above) plus
        # crop transpiration, tracked as vapor pressure (kPa). ---
        vapor_out_kpa = _saturation_vapor_pressure_kpa(temp_out_c) * rh_out_pct / 100.0
        vapor_after_vent = vapor_out_kpa + (state.vapor_pressure_kpa - vapor_out_kpa) * math.exp(-ach * dt_hours)

        transpiration_kg = transpiration_kg_per_hour * dt_hours
        moles_water = transpiration_kg * 1000.0 / WATER_MOLAR_MASS_G_MOL
        temp_in_kelvin = temp_new + 273.15
        delta_vapor_kpa = moles_water * GAS_CONSTANT_J_MOL_K * temp_in_kelvin / self.geometry.volume_m3 / 1000.0

        saturation_kpa = _saturation_vapor_pressure_kpa(temp_new)
        vapor_new = min(vapor_after_vent + delta_vapor_kpa, saturation_kpa)  # cap at 100% RH, no condensation modeled

        rh_in_pct = vapor_new / saturation_kpa * 100.0
        vpd_kpa = saturation_kpa - vapor_new

        return ClimateStepResult(
            state=ClimateState(temp_in_c=temp_new, co2_in_ppm=co2_new, vapor_pressure_kpa=vapor_new),
            heat_used_kw=heat_used_kw,
            heat_dumped_kw=heat_dumped_kw,
            vent_ach=ach,
            co2_injected_kg=injected_kg,
            co2_dumped_kg=co2_dumped_kg,
            rh_in_pct=rh_in_pct,
            vpd_kpa=vpd_kpa,
        )
