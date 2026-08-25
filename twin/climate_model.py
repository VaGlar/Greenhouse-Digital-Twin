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

Thermal screen: fully automatic, deployed whenever any of three conditions
hold (see _screen_should_deploy): night, projected overheating (shade helps
unconditionally), or a cold hour where the CHP can't keep up AND deploying
would net-help (the screen cuts transmission loss but -- being the same
"55% shading / 55% energy saving" fabric per the vendor quote -- also cuts
solar gain, so on a cold-but-sunny hour closing it can lose more heat than
it saves; a real controller wouldn't do that, so neither does this one).
Modeled as a simple deployed/retracted toggle, not a continuous position.

Fan-pad evaporative cooling: an optional, config-toggleable feature
(control.fan_pad_cooling_enabled, off by default). When on, air drawn in by
active (above-baseline) ventilation is treated as pre-cooled AND
pre-humidified by wet pads before it reaches the greenhouse -- both effects
together, since the pad process is adiabatic (the heat removed evaporating
water into the air is exactly what humidifies it). See
_fan_pad_outdoor_conditions.

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
# PLACEHOLDER: degrees above vent_setpoint over which ventilation ramps from vent_min_ach to
# vent_max_ach.
VENT_RAMP_BAND_C = 5.0


def _saturation_vapor_pressure_kpa(temp_c: float) -> float:
    """Tetens/Magnus formula, kPa. Standard meteorological equation (e.g. FAO-56
    Penman-Monteith reference, Allen et al. 1998, eq. 11) -- not a model assumption."""
    return 0.6108 * math.exp(17.27 * temp_c / (temp_c + 237.3))


def _dew_point_c(vapor_pressure_kpa: float) -> float:
    """Inverse of the Tetens formula -- the temperature at which the given vapor
    pressure would be saturating. Standard meteorological formula, not an assumption."""
    vapor_pressure_kpa = max(vapor_pressure_kpa, 1e-6)
    ln_term = math.log(vapor_pressure_kpa / 0.6108)
    return 237.3 * ln_term / (17.27 - ln_term)


def _wet_bulb_temp_c(temp_c: float, rh_pct: float) -> float:
    """Stull (2011) empirical approximation of wet-bulb temperature from dry-bulb
    temperature and relative humidity -- standard meteorological formula, not a model
    assumption. Source: Stull, R., "Wet-Bulb Temperature from Relative Humidity and Air
    Temperature", J. Applied Meteorology and Climatology, 50(11), 2267-2269 (2011).
    Valid roughly over -20 to 50C and 5-99% RH, which covers this project's weather data."""
    rh = max(5.0, min(99.0, rh_pct))
    return (
        temp_c * math.atan(0.151977 * math.sqrt(rh + 8.313659))
        + math.atan(temp_c + rh)
        - math.atan(rh - 1.676331)
        + 0.00391838 * rh**1.5 * math.atan(0.023101 * rh)
        - 4.686035
    )


@dataclass
class ClimateState:
    temp_in_c: float
    co2_in_ppm: float
    vapor_pressure_kpa: float = 1.0  # ~65% RH at 20C; overwritten by the first step anyway

    @property
    def vpd_kpa(self) -> float:
        """Vapor pressure deficit -- fed to the crop model's stomatal/photosynthesis response."""
        return _saturation_vapor_pressure_kpa(self.temp_in_c) - self.vapor_pressure_kpa


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
    condensed_kg: float
    dehumidified_kg: float
    screen_deployed: bool
    # Transmission-loss reduction actually realized this hour because the screen was
    # deployed (0 if retracted) -- a direct physical quantity, not a counterfactual
    # second simulation. Used to report "energy saved by the screen" to the user.
    heat_loss_avoided_kw: float
    fan_pad_active: bool


class GreenhouseClimateModel:
    def __init__(self, geometry: GeometryParams, chp: CHPParams, control: ClimateControlParams):
        self.geometry = geometry
        self.chp = chp
        self.control = control
        self._thermal_capacity_j_k = control.effective_heat_capacity_j_m2k * geometry.area_m2

    def _ventilated_temp(
        self, temp_before_c: float, temp_out_c: float, ach: float, dt_hours: float, vent_setpoint: float
    ) -> float:
        """One hour of ventilation cooling at the given ACH. Bug fix 2026-08-25: the naive linear
        removal (ach * delta_t, applied for the full hour) overshoots badly when ach and delta_t
        are both large -- e.g. a cold, sunny day: solar gain pushes temp well above vent_setpoint,
        the ramp logic below correctly reacts with a high ach, but removing a full hour's worth of
        heat at that rate against a huge indoor-outdoor gradient blew straight through vent_setpoint
        and crashed to outdoor air temperature (once literally hit exactly, confirmed via a real
        low-temp run: indoor == outdoor == 3.91C at 11:00, with heat_used_kw=0 because the crash
        happened via ventilation *after* the heating decision, and vent_ach spiked to 6.4). A real
        thermostatic vent controller stops removing heat once it reaches its target (vent_setpoint)
        rather than continuing until indoor matches outdoor -- floor the result there instead,
        except for the always-present baseline leakage (ach == vent_min_ach), which is passive
        exchange, not active regulation, and should keep drifting toward outdoor air normally."""
        dt_s = dt_hours * 3600.0
        c_total = self._thermal_capacity_j_k
        delta_t = temp_before_c - temp_out_c
        vent_removal_w = ach * self.geometry.volume_m3 * AIR_VOLUMETRIC_HEAT_CAPACITY_J_M3K / 3600.0 * delta_t
        temp_after = temp_before_c - vent_removal_w * dt_s / c_total
        if delta_t > 0:
            floor = max(temp_out_c, vent_setpoint) if ach > self.control.vent_min_ach else temp_out_c
            temp_after = max(temp_after, floor)
        return temp_after

    def _fan_pad_outdoor_conditions(self, temp_out_c: float, rh_out_pct: float) -> tuple[float, float]:
        """Effective outdoor air (temperature, vapor pressure kPa) after passing through
        fan-and-pad evaporative cooling pads, if the greenhouse has them and they're
        engaged. The pads move air a fraction (fan_pad_efficiency) of the way from raw
        outdoor dry-bulb conditions toward saturation at the outdoor wet-bulb temperature.
        Temperature and vapor pressure move together along this same fraction because the
        process is adiabatic (approximately constant wet-bulb): the heat removed from the
        air goes into evaporating water into it, so pad-cooled air is necessarily also
        pad-humidified -- this is what lets a fan-pad system cool the greenhouse below raw
        outdoor air temperature, at the cost of raising the humidity ventilation brings in.
        Returns raw outdoor conditions unchanged when the toggle is off."""
        vapor_out_kpa = _saturation_vapor_pressure_kpa(temp_out_c) * rh_out_pct / 100.0
        if not self.control.fan_pad_cooling_enabled:
            return temp_out_c, vapor_out_kpa
        wet_bulb_c = _wet_bulb_temp_c(temp_out_c, rh_out_pct)
        eff = self.control.fan_pad_efficiency
        temp_pad_c = temp_out_c - eff * (temp_out_c - wet_bulb_c)
        vapor_pad_kpa = vapor_out_kpa + eff * (_saturation_vapor_pressure_kpa(wet_bulb_c) - vapor_out_kpa)
        return temp_pad_c, vapor_pad_kpa

    def decide_screen_deployment(
        self,
        state: ClimateState,
        hour: int,
        temp_out_c: float,
        solar_rad_w_m2: float,
        dt_hours: float,
        rh_out_pct: float = 60.0,
    ) -> bool:
        """Decide deploy/retract for this hour, before the screen's own effect is applied to
        the energy balance -- see module docstring for the 3 criteria. Public so twin/simulate.py
        can compute this once per hour and feed the same decision to both this model (energy
        balance) and the crop model (shaded light for photosynthesis), keeping them consistent."""
        if not self.control.is_daytime(hour):
            return True  # night

        dt_s = dt_hours * 3600.0
        c_total = self._thermal_capacity_j_k
        setpoint = self.control.heating_setpoint(hour)
        vent_setpoint = setpoint + self.control.vent_temp_margin_c
        q_solar_w_full = solar_rad_w_m2 * self.geometry.area_m2 * self.geometry.cover_transmissivity
        q_trans_loss_w_full = self.geometry.cover_u_value_w_m2k * self.geometry.cover_area_m2 * (
            state.temp_in_c - temp_out_c
        )

        # "Too hot" means ventilation alone (even fully ramped) won't be enough -- not merely
        # "ventilation has started ramping up", which is its normal job. Checked by actually
        # applying max-ACH ventilation (via the same _ventilated_temp helper step() uses) to the
        # unscreened projection, rather than comparing the raw pre-ventilation number to a fixed
        # margin -- the fixed-margin version (vent_setpoint + VENT_RAMP_BAND_C) made the screen
        # shade ~59% of all daytime hours and cut yield ~17% for no real overheating benefit; see
        # docs/assumptions/climate-control.md for that finding and this one.
        # If this greenhouse has fan-pad cooling, max ventilation draws in pad-cooled (not
        # raw outdoor) air -- check against that, so the screen doesn't shade unnecessarily
        # on a hot-but-dry day the pads could have handled alone.
        temp_out_c_for_vent, _ = self._fan_pad_outdoor_conditions(temp_out_c, rh_out_pct)
        temp_pred_no_screen = state.temp_in_c + (q_solar_w_full - q_trans_loss_w_full) * dt_s / c_total
        temp_after_max_vent = self._ventilated_temp(
            temp_pred_no_screen, temp_out_c_for_vent, self.control.vent_max_ach, dt_hours, vent_setpoint
        )
        if temp_after_max_vent > vent_setpoint + 0.01:
            return True  # even full ventilation can't hold vent_setpoint -- shading actually needed

        heat_available_w = self.chp.heat_available_kw * 1000.0
        required_w_no_screen = max(0.0, (setpoint - temp_pred_no_screen) * c_total / dt_s)
        if required_w_no_screen <= self.control.chp_heat_margin_fraction * heat_available_w:
            return False  # CHP has enough headroom, no need to insulate at the cost of light

        # Cold and CHP can't comfortably keep up -- but the screen also blocks solar
        # gain, so only close it if that trade actually reduces the heat deficit.
        trans_loss_saved_w = max(0.0, q_trans_loss_w_full) * self.control.screen_energy_saving_fraction
        solar_lost_w = max(0.0, q_solar_w_full) * self.control.screen_energy_saving_fraction
        return trans_loss_saved_w > solar_lost_w

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
        screen_deployed: bool | None = None,
    ) -> ClimateStepResult:
        dt_s = dt_hours * 3600.0
        c_total = self._thermal_capacity_j_k

        # --- Energy balance: solar gain vs. transmission loss ---
        setpoint = self.control.heating_setpoint(hour)
        vent_setpoint = setpoint + self.control.vent_temp_margin_c
        q_solar_w_full = solar_rad_w_m2 * self.geometry.area_m2 * self.geometry.cover_transmissivity
        q_trans_loss_w_full = self.geometry.cover_u_value_w_m2k * self.geometry.cover_area_m2 * (
            state.temp_in_c - temp_out_c
        )
        if screen_deployed is None:
            screen_deployed = self.decide_screen_deployment(state, hour, temp_out_c, solar_rad_w_m2, dt_hours)
        # Thermal screen: same fabric provides both effects whenever deployed -- cuts
        # transmission heat loss AND solar gain by its rated fraction (see module docstring).
        if screen_deployed:
            q_solar_w = q_solar_w_full * (1.0 - self.control.screen_energy_saving_fraction)
            q_trans_loss_w = q_trans_loss_w_full * (1.0 - self.control.screen_energy_saving_fraction)
        else:
            q_solar_w = q_solar_w_full
            q_trans_loss_w = q_trans_loss_w_full
        heat_loss_avoided_kw = max(0.0, q_trans_loss_w_full - q_trans_loss_w) / 1000.0
        net_w = q_solar_w - q_trans_loss_w
        temp_pred = state.temp_in_c + net_w * dt_s / c_total

        # --- Heating from the CHP's fixed, constant heat supply ---
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
        excess = max(0.0, temp_after_heat - vent_setpoint)
        ramp_fraction = min(1.0, excess / VENT_RAMP_BAND_C)
        ach = self.control.vent_min_ach + (self.control.vent_max_ach - self.control.vent_min_ach) * ramp_fraction

        # Fan-pad cooling only engages alongside active (above-baseline) ventilation -- a
        # real system runs its pads together with the exhaust fans, not during passive
        # leakage. When active, ventilation draws in pad-cooled (and pad-humidified) air
        # instead of raw outdoor air, for both the temperature and humidity balances below.
        fan_pad_active = self.control.fan_pad_cooling_enabled and ach > self.control.vent_min_ach
        if fan_pad_active:
            temp_out_c_for_vent, vapor_out_kpa = self._fan_pad_outdoor_conditions(temp_out_c, rh_out_pct)
        else:
            temp_out_c_for_vent = temp_out_c
            vapor_out_kpa = _saturation_vapor_pressure_kpa(temp_out_c) * rh_out_pct / 100.0

        temp_new = self._ventilated_temp(temp_after_heat, temp_out_c_for_vent, ach, dt_hours, vent_setpoint)

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

        # --- Humidity balance: ventilation exchange (same ach and, if fan-pad cooling is
        # engaged, the same pad-humidified vapor_out_kpa as above) plus crop transpiration,
        # tracked as vapor pressure (kPa). ---
        vapor_after_vent = vapor_out_kpa + (state.vapor_pressure_kpa - vapor_out_kpa) * math.exp(-ach * dt_hours)

        transpiration_kg = transpiration_kg_per_hour * dt_hours
        moles_water = transpiration_kg * 1000.0 / WATER_MOLAR_MASS_G_MOL
        temp_in_kelvin = temp_new + 273.15
        delta_vapor_kpa = moles_water * GAS_CONSTANT_J_MOL_K * temp_in_kelvin / self.geometry.volume_m3 / 1000.0

        vapor_before_condensation = vapor_after_vent + delta_vapor_kpa

        # --- Passive condensation on the (colder) cover surface: real dehumidification
        # even when the bulk air is well below 100% RH, since the cover surface can sit
        # below the air's dew point. Cover surface temp approximated as a fixed fraction
        # of the way from outdoor to indoor air temp (thin-film cover, most thermal
        # resistance is in the air boundary layers, not the plastic itself).
        cover_temp_c = temp_out_c + (temp_new - temp_out_c) * self.control.cover_surface_temp_fraction
        dew_point_c = _dew_point_c(vapor_before_condensation)
        if cover_temp_c < dew_point_c:
            cover_saturation_kpa = _saturation_vapor_pressure_kpa(cover_temp_c)
            vapor_after_condensation = cover_saturation_kpa + (
                vapor_before_condensation - cover_saturation_kpa
            ) * math.exp(-self.control.condensation_rate_constant * dt_hours)
        else:
            vapor_after_condensation = vapor_before_condensation
        condensed_kg = max(0.0, vapor_before_condensation - vapor_after_condensation) * 1000.0 / (
            GAS_CONSTANT_J_MOL_K * temp_in_kelvin
        ) * self.geometry.volume_m3 * WATER_MOLAR_MASS_G_MOL / 1000.0

        # --- Active dehumidification: setpoint controller (representing the OptiClima
        # cooling/dehumidification panels) that removes moisture toward its target ceiling,
        # capped at a real removal capacity (dehumidification_capacity_kg_water_per_hour).
        # Bug fix 2026-08-25: previously unconstrained (always assumed sufficient to reach
        # the setpoint in a single hour) -- no real spec was available for this system, so
        # this is a PLACEHOLDER capacity sourced to comparable real systems, not a measured
        # spec for this exact unit. See docs/assumptions/climate-control.md.
        saturation_kpa = _saturation_vapor_pressure_kpa(temp_new)
        dehum_target_kpa = saturation_kpa * self.control.dehumidification_setpoint_pct / 100.0
        demanded_removal_kpa = max(0.0, vapor_after_condensation - dehum_target_kpa)
        demanded_kg = demanded_removal_kpa * 1000.0 / (
            GAS_CONSTANT_J_MOL_K * temp_in_kelvin
        ) * self.geometry.volume_m3 * WATER_MOLAR_MASS_G_MOL / 1000.0
        max_removal_kg = self.control.dehumidification_capacity_kg_water_per_hour * dt_hours
        dehumidified_kg = min(demanded_kg, max_removal_kg)
        removed_kpa = dehumidified_kg * 1000.0 / WATER_MOLAR_MASS_G_MOL * GAS_CONSTANT_J_MOL_K * temp_in_kelvin / (
            self.geometry.volume_m3 * 1000.0
        )
        vapor_after_dehum = vapor_after_condensation - removed_kpa

        vapor_new = min(vapor_after_dehum, saturation_kpa)  # final safety cap at 100% RH

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
            condensed_kg=condensed_kg,
            dehumidified_kg=dehumidified_kg,
            screen_deployed=screen_deployed,
            heat_loss_avoided_kw=heat_loss_avoided_kw,
            fan_pad_active=fan_pad_active,
        )
