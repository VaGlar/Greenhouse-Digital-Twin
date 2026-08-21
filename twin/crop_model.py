"""Tomato crop growth model (TOMGRO-lite).

Canopy-level photosynthesis driven by light, CO2 and temperature, coupled
each hour to the climate model's greenhouse air state. Gross assimilation
minus maintenance respiration accumulates as dry matter; a growth-stage
dependent partitioning fraction sends part of that dry matter to fruit,
which is converted to fresh-weight yield.

This is a simplified, illustrative model (not a calibrated TOMGRO port).
Cardinal temperatures, light/CO2 half-saturation constants and partition
fractions are literature-typical defaults for greenhouse tomato and should
be recalibrated once real yield/sensor data is available.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from twin.params import CropParams

CO2_MOLAR_MASS_G_MOL = 44.0
CH2O_MOLAR_MASS_G_MOL = 30.0
CO2_TO_DRY_MATTER_FACTOR = CH2O_MOLAR_MASS_G_MOL / CO2_MOLAR_MASS_G_MOL  # g DM per g CO2 fixed

# Canopy photosynthesis parameters (typical greenhouse tomato, illustrative).
# See docs/assumptions/crop-model.md for the full source audit of every value below.
P_MAX_UMOL_M2_LEAF_S = 20.0  # SOURCED, conservative end of the 20-40 umol/m2/s range reported for tomato
# (Growth and Photosynthetic Response of Tomato to Nutrient Solution Concentration, researchgate 258515123 —
#  journal article, specific page not confirmed, figure taken from search-result summary)
LIGHT_HALF_SAT_W_M2 = 200.0  # PLACEHOLDER, plausible order of magnitude — not individually sourced
CO2_HALF_SAT_PPM = 200.0  # PLACEHOLDER, plausible shape (saturates ~1000-1200ppm) — not individually sourced
T_MIN_C, T_OPT_C, T_MAX_C = 10.0, 27.0, 35.0  # SOURCED: T_OPT raised from 24C to 27C to match photosynthesis-
# specific studies reporting optimum 25-35C (tomato retains 50% of photosynthetic rate even at 47C) — Frontiers
# 10.3389/fpls.2017.00365; researchgate 323225604 review. T_MIN left unchanged (not part of this pass).
MAINTENANCE_RESPIRATION_FRACTION_PER_DAY = 0.015  # PLACEHOLDER, plausible order of magnitude — not individually sourced

# Canopy transpiration (drives the climate model's humidity balance).
CANOPY_LIGHT_EXTINCTION_COEFF = 0.75  # SOURCED: Beer-Lambert k for high-wire tomato canopies, reported 0.7-0.9
# (general canopy light-interception literature; see docs/assumptions/crop-model.md)
TRANSPIRATION_ENERGY_FRACTION = 0.70  # SOURCED: latent heat flux is 66.4-71.7% of net radiation intercepted
# by a greenhouse tomato canopy (measured study); see docs/assumptions/crop-model.md
LATENT_HEAT_OF_VAPORIZATION_J_KG = 2.45e6  # physical constant, water at ~20C (standard meteorological value,
# e.g. FAO-56 Penman-Monteith reference)


@dataclass
class CropState:
    days_after_planting: float = 0.0
    leaf_area_index: float = 0.05
    standing_dry_matter_g_m2: float = 5.0  # total plant dry matter per m2 ground area
    fruit_dry_matter_g_m2: float = 0.0
    fruit_fresh_yield_kg_m2: float = 0.0


@dataclass
class CropStepResult:
    state: CropState
    gross_assimilation_kg_co2_m2_hour: float
    transpiration_kg_m2_hour: float


def _temperature_response(temp_c: float) -> float:
    """Bell-shaped response, 0 outside [T_MIN, T_MAX], 1 at T_OPT."""
    if temp_c <= T_MIN_C or temp_c >= T_MAX_C:
        return 0.0
    # Normalized product function (Yin et al. style), smooth and bounded in [0, 1].
    num = (temp_c - T_MIN_C) * (T_MAX_C - temp_c)
    den = (T_OPT_C - T_MIN_C) * (T_MAX_C - T_OPT_C)
    return max(0.0, (num / den))


def _light_response(solar_rad_w_m2: float) -> float:
    return solar_rad_w_m2 / (solar_rad_w_m2 + LIGHT_HALF_SAT_W_M2) if solar_rad_w_m2 > 0 else 0.0


def _co2_response(co2_ppm: float) -> float:
    return co2_ppm / (co2_ppm + CO2_HALF_SAT_PPM)


def _lai(params: CropParams, days_after_planting: float) -> float:
    """Logistic growth from ~0 to an effective lai_max over lai_ramp_days.

    lai_max is literature-typical for a canopy planted at
    reference_density_plants_per_m2; a sparser planting closes its canopy
    at a proportionally lower peak LAI (fewer plants per m2 -> less total
    leaf area, up to the point of full canopy closure), a denser one is
    capped at lai_max (extra plants beyond canopy closure add negligible
    net leaf area in this simplified model).
    """
    density_factor = min(1.0, params.density_plants_per_m2 / params.reference_density_plants_per_m2)
    effective_lai_max = params.lai_max * density_factor
    if days_after_planting <= 0:
        return 0.05
    x = days_after_planting / params.lai_ramp_days
    logistic = 1.0 / (1.0 + math.exp(-10 * (x - 0.5)))
    return max(0.05, effective_lai_max * logistic)


def _fruit_partition_fraction(params: CropParams, days_after_planting: float) -> float:
    if days_after_planting < params.fruiting_start_days:
        return 0.0
    ramp = (days_after_planting - params.fruiting_start_days) / params.fruiting_ramp_days
    return params.fruit_partition_fraction_max * min(1.0, max(0.0, ramp))


class TomatoCropModel:
    def __init__(self, params: CropParams, ground_area_m2: float):
        self.params = params
        self.ground_area_m2 = ground_area_m2

    def step(
        self,
        state: CropState,
        temp_in_c: float,
        co2_in_ppm: float,
        solar_rad_w_m2: float,
        dt_hours: float,
    ) -> CropStepResult:
        lai = _lai(self.params, state.days_after_planting)

        f_light = _light_response(solar_rad_w_m2)
        f_co2 = _co2_response(co2_in_ppm)
        f_temp = _temperature_response(temp_in_c)

        p_gross_umol_m2_leaf_s = P_MAX_UMOL_M2_LEAF_S * f_light * f_co2 * f_temp
        p_gross_umol_m2_ground_s = p_gross_umol_m2_leaf_s * lai

        # mol CO2 / m2 ground / hour -> kg CO2 / m2 ground / hour
        gross_assimilation_kg_co2_m2_hour = (
            p_gross_umol_m2_ground_s * 3600 * 1e-6 * CO2_MOLAR_MASS_G_MOL / 1000.0
        )

        gross_dry_matter_g_m2_hour = (
            gross_assimilation_kg_co2_m2_hour * 1000.0 * CO2_TO_DRY_MATTER_FACTOR
        )

        # Maintenance respiration: proportional to standing biomass, scaled by
        # the same temperature response (warmer -> faster respiration), spread
        # evenly across the day rather than only during daylight.
        respiration_g_m2_hour = (
            state.standing_dry_matter_g_m2
            * MAINTENANCE_RESPIRATION_FRACTION_PER_DAY
            / 24.0
            * max(f_temp, 0.3)
        )

        net_dry_matter_g_m2_hour = gross_dry_matter_g_m2_hour * dt_hours - respiration_g_m2_hour * dt_hours
        # Maintenance respiration legitimately consumes standing biomass hour to hour
        # (real plants do lose dry matter to respiration overnight) -- only floored at
        # zero as a physical sanity bound. This is distinct from senescence/abscission
        # (programmed tissue death/leaf drop), which is a separate process still not
        # modeled here. Fixed 2026-08-20: an earlier `max(current, current+net)` clamp
        # discarded every hour's respiration loss entirely, silently making nighttime
        # temperature (and therefore the thermal screen) have zero effect on yield.
        new_standing_dm = max(0.0, state.standing_dry_matter_g_m2 + net_dry_matter_g_m2_hour)

        fruit_fraction = _fruit_partition_fraction(self.params, state.days_after_planting)
        new_growth_g_m2 = max(0.0, net_dry_matter_g_m2_hour)
        fruit_dm_increment = new_growth_g_m2 * fruit_fraction

        new_fruit_dm = state.fruit_dry_matter_g_m2 + fruit_dm_increment
        new_fruit_fresh_yield_kg_m2 = new_fruit_dm / self.params.dry_matter_content_fruit / 1000.0

        new_state = CropState(
            days_after_planting=state.days_after_planting + dt_hours / 24.0,
            leaf_area_index=lai,
            standing_dry_matter_g_m2=new_standing_dm,
            fruit_dry_matter_g_m2=new_fruit_dm,
            fruit_fresh_yield_kg_m2=new_fruit_fresh_yield_kg_m2,
        )

        # Canopy transpiration: fraction of solar radiation intercepted by the canopy
        # (Beer-Lambert, LAI-driven) that is converted to latent heat (water vapor),
        # feeding the climate model's humidity balance. Zero at night (no solar input).
        canopy_interception = 1.0 - math.exp(-CANOPY_LIGHT_EXTINCTION_COEFF * lai)
        absorbed_solar_w_m2 = solar_rad_w_m2 * canopy_interception
        latent_heat_w_m2 = absorbed_solar_w_m2 * TRANSPIRATION_ENERGY_FRACTION
        transpiration_kg_m2_hour = latent_heat_w_m2 * 3600.0 / LATENT_HEAT_OF_VAPORIZATION_J_KG

        return CropStepResult(
            state=new_state,
            gross_assimilation_kg_co2_m2_hour=gross_assimilation_kg_co2_m2_hour,
            transpiration_kg_m2_hour=transpiration_kg_m2_hour,
        )
