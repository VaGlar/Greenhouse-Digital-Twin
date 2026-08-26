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
CO2_HALF_SAT_PPM = 375.0  # SOURCED, raised from 200 on 2026-08-20: the biochemical Rubisco Km for CO2
# (Ci-based, ~270-300 ppm at 25C in FvCB-model literature) needs adjusting for the Ci/Ca gradient
# (Ci/Ca ~0.7-0.8 for well-watered C3 plants) to translate into a Ca-based (ambient/greenhouse air
# CO2) constant like this one -- giving ~340-430 ppm; used the midpoint. On its own, this factor's
# rectangular-hyperbola shape has elasticity <1 (% output gain always below % input gain), so it
# alone can't reproduce the ~56-74% season-long yield gain a study reports from 500->700ppm CO2 --
# see CO2_LAI_BOOST_MAX below for the channel that closes that gap. Confirmed against a sensitivity
# sweep (K=100..600): 375 lands the model's ambient(420)->700ppm yield gain at ~56%, right at the
# low end of that reported range. See docs/assumptions/crop-model.md.
CO2_AMBIENT_REFERENCE_PPM = 420.0  # baseline CO2 the LAI boost below is measured relative to
CO2_LAI_BOOST_MAX = 0.2688  # SOURCED: CO2 enrichment's real yield gain comes mostly from bigger leaf
# area (LAI), not just faster instantaneous photosynthesis -- a study found LAI +26.88% at 700ppm
# vs ambient (compounds over the season: more canopy -> more total assimilation every subsequent
# hour). This is the season-long "compounding" channel the instantaneous CO2_HALF_SAT_PPM factor
# above structurally cannot capture on its own. See docs/assumptions/crop-model.md and
# docs/papers/co2-lai-growth-boost.md.
CO2_SATURATION_PPM = 700.0  # SOURCED: tomato study testing 500/700/850/1000 ppm found 700ppm optimal,
# no further yield benefit above it -- response plateaus here instead of rising indefinitely.
# See docs/assumptions/crop-model.md and docs/papers/tomato-co2-optimum-700ppm.md
T_MIN_C, T_OPT_C, T_MAX_C = 10.0, 27.0, 35.0  # SOURCED: T_OPT raised from 24C to 27C to match photosynthesis-
# specific studies reporting optimum 25-35C (tomato retains 50% of photosynthetic rate even at 47C) — Frontiers
# 10.3389/fpls.2017.00365; researchgate 323225604 review. T_MIN left unchanged (not part of this pass).
MAINTENANCE_RESPIRATION_FRACTION_PER_DAY = 0.015  # PLACEHOLDER, plausible order of magnitude — not individually sourced

# Fruit-set temperature sensitivity -- SOURCED, added 2026-08-25. Deliberately separate from
# and much narrower than T_MIN_C/T_OPT_C/T_MAX_C above: those describe photosynthesis, which
# tomato leaves tolerate over a wide range (retaining 50% of rate even at 47C). Pollen viability
# and pollen tube growth -- what actually determines whether a flower becomes a fruit -- are far
# more temperature-sensitive: below ~55F (12.8C) promotes blossom drop and poor pollen vigor;
# ideal fruit set sits in a narrow 60-70F (15.6-21.1C) window; above ~75F (24C) interferes with
# pollen tube growth and causes blossom drop. See docs/papers/tomato-fruit-set-temperature-sensitivity.md.
FRUIT_SET_T_MIN_C, FRUIT_SET_T_OPT_C, FRUIT_SET_T_MAX_C = 12.0, 18.0, 24.0
# PLACEHOLDER: half-life (hours) of the temperature EMA that _fruit_set_temp_response is
# evaluated against, instead of the instantaneous hourly temp_in_c. Without this, a cold
# night has literally zero effect on fruit-set quality in this model -- net dry matter is
# never positive at night (no light), so a fruit-set penalty gated on "hours with positive
# growth" only ever sees daytime temperature, no matter how cold the preceding night was.
# 12h is an engineering choice representing the rough timescale over which flower/pollen-tube
# development integrates recent conditions (not an instantaneous snapshot) -- not calibrated
# to a specific study.
FRUIT_SET_TEMP_EMA_HALF_LIFE_HOURS = 12.0

# Canopy transpiration (drives the climate model's humidity balance).
CANOPY_LIGHT_EXTINCTION_COEFF = 0.75  # SOURCED: Beer-Lambert k for high-wire tomato canopies, reported 0.7-0.9
# (general canopy light-interception literature; see docs/assumptions/crop-model.md)
TRANSPIRATION_ENERGY_FRACTION = 0.70  # SOURCED: latent heat flux is 66.4-71.7% of net radiation intercepted
# by a greenhouse tomato canopy (measured study); see docs/assumptions/crop-model.md
LATENT_HEAT_OF_VAPORIZATION_J_KG = 2.45e6  # physical constant, water at ~20C (standard meteorological value,
# e.g. FAO-56 Penman-Monteith reference)

# VPD (vapor pressure deficit) response of photosynthesis -- stomata close under high VPD
# (water-stress avoidance) and gas exchange suffers near saturation (low VPD) too.
VPD_MIN_KPA = 0.2  # SOURCED: below the ~0.3-1.0 kPa cited optimal range
VPD_OPT_KPA = 0.85  # SOURCED: mid of the 0.3-1.0 kPa optimal range / near the ~1 kPa reported peak
VPD_MAX_KPA = 2.0  # SOURCED: "suitable VPD for tomato growth is less than 2 kPa"; stomatal closure
# accelerates from ~1.5 kPa. See docs/assumptions/crop-model.md.


@dataclass
class CropState:
    days_after_planting: float = 0.0
    leaf_area_index: float = 0.05
    standing_dry_matter_g_m2: float = 5.0  # total plant dry matter per m2 ground area
    fruit_dry_matter_g_m2: float = 0.0
    fruit_fresh_yield_kg_m2: float = 0.0
    # Running maximum standing_dry_matter_g_m2 has ever reached (g/m2) -- see
    # TomatoCropModel.step for why this exists: respiration is charged against this,
    # not the current (freely shrinkable) standing_dry_matter_g_m2. Without it, a bad
    # night's respiration loss reduced standing biomass with no other consequence --
    # and since LAI doesn't depend on standing biomass, *smaller* biomass actually
    # meant *less* future respiration to pay, with photosynthetic capacity completely
    # unaffected. That made burning biomass via wasteful (warm) nighttime respiration
    # a pure win: less biomass, therefore a permanently lower future respiration
    # bill, for free. Charging respiration against the high-water mark instead means
    # a bad night still costs real biomass, but doesn't also discount the future.
    respiration_reference_g_m2: float = 5.0
    # Exponential moving average of temp_in_c (see FRUIT_SET_TEMP_EMA_HALF_LIFE_HOURS) --
    # fruit set depends on recent flower/pollen-tube development, not an instantaneous
    # temperature snapshot, so a cold night needs to carry forward into the following
    # day's fruit-set quality rather than being invisible once daytime growth resumes.
    recent_temp_ema_c: float = 20.0


@dataclass
class CropStepResult:
    state: CropState
    gross_assimilation_kg_co2_m2_hour: float
    transpiration_kg_m2_hour: float
    # The _fruit_set_temp_response factor evaluated this hour (0-1) -- already computed
    # internally to gate fruit dry-matter partitioning, now also exposed directly as a
    # real "fruit set %" a grower could read, rather than staying an invisible internal
    # multiplier.
    fruit_set_fraction: float


def _temperature_response(temp_c: float) -> float:
    """Bell-shaped response, 0 outside [T_MIN, T_MAX], 1 at T_OPT.

    Fixed 2026-08-20: the normalized product function (Yin et al. style) only
    equals exactly 1 at T_OPT by construction -- when T_OPT isn't equidistant
    from T_MIN/T_MAX (it isn't here: 27 vs. midpoint 22.5), the raw parabola's
    true peak sits elsewhere and the ratio can exceed 1 there (was hitting
    ~1.15 around 20-25C, exactly this greenhouse's normal operating range,
    silently over-boosting photosynthesis this whole time). Clamped at 1.0.
    """
    if temp_c <= T_MIN_C or temp_c >= T_MAX_C:
        return 0.0
    # Normalized product function (Yin et al. style), smooth and bounded in [0, 1].
    num = (temp_c - T_MIN_C) * (T_MAX_C - temp_c)
    den = (T_OPT_C - T_MIN_C) * (T_MAX_C - T_OPT_C)
    return min(1.0, max(0.0, (num / den)))


def _fruit_set_temp_response(temp_c: float) -> float:
    """Bell-shaped response, 0 outside [FRUIT_SET_T_MIN, FRUIT_SET_T_MAX], 1 at
    FRUIT_SET_T_OPT -- same normalized-product-function shape as
    _temperature_response, but far narrower: pollen viability and fruit set are much
    more temperature-sensitive than photosynthesis itself (see module constants).

    Added 2026-08-25: closes a gap the user found by testing extreme night setpoints
    -- with only _temperature_response (which barely penalizes cold, since it's
    calibrated for photosynthesis's wide tolerance) driving respiration, colder
    nights always looked *better* for yield with no floor, all the way down to 5C.
    Real tomato fruit set fails at both ends of a much narrower window than
    photosynthesis tolerates; this response multiplies the fruit partition fraction
    directly so an unrealistically cold (or hot) night now costs real yield."""
    if temp_c <= FRUIT_SET_T_MIN_C or temp_c >= FRUIT_SET_T_MAX_C:
        return 0.0
    num = (temp_c - FRUIT_SET_T_MIN_C) * (FRUIT_SET_T_MAX_C - temp_c)
    den = (FRUIT_SET_T_OPT_C - FRUIT_SET_T_MIN_C) * (FRUIT_SET_T_MAX_C - FRUIT_SET_T_OPT_C)
    return min(1.0, max(0.0, num / den))


def _canopy_light_response(solar_rad_w_m2: float, lai: float) -> float:
    """Canopy-integrated light response, replacing a flat single-leaf-rate * LAI
    multiplication. Bug fix 2026-08-25: multiplying the top-of-canopy leaf response
    by LAI implicitly assumed every leaf layer sees the same full incident light,
    when lower layers are self-shaded (the same canopy this model already applies
    Beer-Lambert attenuation to for transpiration, via canopy_interception below --
    just not, until now, for photosynthesis). That inconsistency overestimated gross
    assimilation at every light level, but far more at low light than high light
    (self-shading matters less when incident light is already high enough to
    saturate even the lower layers) -- flattening the model's seasonal light
    sensitivity: a real 150-300 W/m2 winter-to-summer difference in average incident
    solar only moved yield by ~37% instead of properly tracking it.

    Standard result for a Michaelis-Menten leaf response f(I) = I/(I+K) under Beer's
    law attenuation I(z) = I0*exp(-k*z) through canopy depth z in [0, LAI]:
    integral of f(I(z)) dz, 0 to LAI = (1/k) * ln[(I0+K) / (I0*exp(-k*LAI)+K)]
    (e.g. de Wit 1965 / Goudriaan-style integrated canopy photosynthesis). This
    replaces a plain top-of-canopy _light_response(solar) * lai in the assimilation calculation --
    already properly bounded (rises with LAI, saturates with light) without an
    extra explicit LAI multiplication."""
    if solar_rad_w_m2 <= 0 or lai <= 0:
        return 0.0
    k = CANOPY_LIGHT_EXTINCTION_COEFF
    numerator = solar_rad_w_m2 + LIGHT_HALF_SAT_W_M2
    denominator = solar_rad_w_m2 * math.exp(-k * lai) + LIGHT_HALF_SAT_W_M2
    return (1.0 / k) * math.log(numerator / denominator)


def _co2_response(co2_ppm: float) -> float:
    """Michaelis-Menten rise up to CO2_SATURATION_PPM, then flat.

    Fixed 2026-08-20: the raw Michaelis-Menten curve rises forever (never
    caps), so yield kept climbing with CO2 setpoints far past what real
    tomato can use. A specific study testing 500/700/850/1000 ppm found
    700 ppm optimal and no further yield benefit above it (see
    docs/assumptions/crop-model.md) -- clamped the input at
    CO2_SATURATION_PPM so the response plateaus there instead of climbing
    indefinitely.
    """
    return min(co2_ppm, CO2_SATURATION_PPM) / (min(co2_ppm, CO2_SATURATION_PPM) + CO2_HALF_SAT_PPM)


def _vpd_response(vpd_kpa: float) -> float:
    """Bell-shaped response, 0 outside [VPD_MIN, VPD_MAX], 1 at VPD_OPT -- same
    normalized product-function shape as _temperature_response, with the same
    clamp at 1.0 (VPD_OPT isn't centered between VPD_MIN/VPD_MAX either)."""
    if vpd_kpa <= VPD_MIN_KPA or vpd_kpa >= VPD_MAX_KPA:
        return 0.0
    num = (vpd_kpa - VPD_MIN_KPA) * (VPD_MAX_KPA - vpd_kpa)
    den = (VPD_OPT_KPA - VPD_MIN_KPA) * (VPD_MAX_KPA - VPD_OPT_KPA)
    return min(1.0, max(0.0, num / den))


def _lai(params: CropParams, days_after_planting: float, co2_ppm: float) -> float:
    """Logistic growth from ~0 to an effective lai_max over lai_ramp_days.

    lai_max is literature-typical for a canopy planted at
    reference_density_plants_per_m2; a sparser planting closes its canopy
    at a proportionally lower peak LAI (fewer plants per m2 -> less total
    leaf area, up to the point of full canopy closure), a denser one is
    capped at lai_max (extra plants beyond canopy closure add negligible
    net leaf area in this simplified model).

    CO2 also boosts effective_lai_max (added 2026-08-20): real tomato grows
    more/bigger leaves under CO2 enrichment, not just faster instantaneous
    photosynthesis -- this is the season-long compounding channel a single
    per-hour multiplier can't represent. Scales linearly from no boost at
    CO2_AMBIENT_REFERENCE_PPM to +CO2_LAI_BOOST_MAX at CO2_SATURATION_PPM,
    reusing the same saturating shape as _co2_response for consistency.
    """
    density_factor = min(1.0, params.density_plants_per_m2 / params.reference_density_plants_per_m2)
    co2_at_ambient = _co2_response(CO2_AMBIENT_REFERENCE_PPM)
    co2_at_saturation = _co2_response(CO2_SATURATION_PPM)
    co2_progress = (_co2_response(co2_ppm) - co2_at_ambient) / (co2_at_saturation - co2_at_ambient)
    co2_lai_factor = 1.0 + CO2_LAI_BOOST_MAX * min(1.0, max(0.0, co2_progress))
    effective_lai_max = params.lai_max * density_factor * co2_lai_factor
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
        vpd_kpa: float = VPD_OPT_KPA,
    ) -> CropStepResult:
        lai = _lai(self.params, state.days_after_planting, co2_in_ppm)

        f_light_canopy = _canopy_light_response(solar_rad_w_m2, lai)
        f_co2 = _co2_response(co2_in_ppm)
        f_temp = _temperature_response(temp_in_c)
        f_vpd = _vpd_response(vpd_kpa)

        # Canopy-integrated already accounts for LAI (self-shading), unlike a flat
        # leaf-rate * LAI multiplication -- see _canopy_light_response.
        p_gross_umol_m2_ground_s = P_MAX_UMOL_M2_LEAF_S * f_light_canopy * f_co2 * f_temp * f_vpd

        # mol CO2 / m2 ground / hour -> kg CO2 / m2 ground / hour
        gross_assimilation_kg_co2_m2_hour = (
            p_gross_umol_m2_ground_s * 3600 * 1e-6 * CO2_MOLAR_MASS_G_MOL / 1000.0
        )

        gross_dry_matter_g_m2_hour = (
            gross_assimilation_kg_co2_m2_hour * 1000.0 * CO2_TO_DRY_MATTER_FACTOR
        )

        # Maintenance respiration: proportional to a *reference* biomass, scaled by
        # the same temperature response (warmer -> faster respiration), spread
        # evenly across the day rather than only during daylight.
        #
        # Bug fix 2026-08-25 (revised same day): the reference used to be the current
        # standing_dry_matter_g_m2 directly. But standing biomass can shrink on a bad
        # (net-negative) hour -- typically every night, since gross assimilation is
        # zero with no light -- and since LAI doesn't depend on standing biomass at
        # all, a smaller pool meant strictly *less* future respiration to pay, with
        # photosynthetic capacity completely unaffected. That made burning biomass via
        # wasteful (warm) nighttime respiration a pure win: real cost that hour, free
        # discount on every future hour's respiration bill.
        #
        # First attempt at a fix used a separate "repay this deficit before any fruit
        # credit" ledger -- it flipped the direction correctly but *also* double-
        # charged the loss (once via the reduced standing_dry_matter_g_m2, which
        # already is a real, legitimate consequence, and again by blocking future
        # fruit credit for an equivalent amount) -- season-total respiration losses on
        # net-negative hours were ~480 g/m2 out of ~1505 g/m2 total gross assimilation
        # (150-day run), all of it diverted a second time away from fruit. Reverted.
        #
        # Fixed properly with `respiration_reference_g_m2`: a running high-water mark
        # of standing_dry_matter_g_m2, which only ever grows, never shrinks with it.
        # Respiration is charged against *this*, so a bad night still costs real
        # biomass (reflected once, in new_standing_dm below) but no longer discounts
        # any future respiration bill -- removing the exploit without charging the
        # same loss twice. Matches how a real plant's actual structure (stems, roots,
        # established leaf tissue) doesn't shrink from one night's negative carbon
        # balance; senescence/abscission remains a separate, still-unmodeled process.
        respiration_reference = max(state.respiration_reference_g_m2, state.standing_dry_matter_g_m2)
        respiration_g_m2_hour = (
            respiration_reference
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
        new_respiration_reference = max(respiration_reference, new_standing_dm)

        fruit_fraction = _fruit_partition_fraction(self.params, state.days_after_planting)
        # Fruit set (not photosynthesis) is the temperature-sensitive step here -- see
        # _fruit_set_temp_response. Evaluated against a temperature EMA, not the
        # instantaneous temp_in_c: net growth (and therefore any fruit credit) is only
        # ever positive during daylight, so gating this purely on the current hour's
        # temperature would make a cold *night* invisible to fruit set entirely --
        # the EMA lets a cold night's chill carry forward into the following day's
        # fruit-set quality, matching how flower/pollen-tube development actually
        # integrates recent conditions rather than an instant snapshot.
        ema_alpha = 1.0 - math.exp(-dt_hours * math.log(2) / FRUIT_SET_TEMP_EMA_HALF_LIFE_HOURS)
        new_temp_ema_c = state.recent_temp_ema_c + ema_alpha * (temp_in_c - state.recent_temp_ema_c)
        f_fruit_set = _fruit_set_temp_response(new_temp_ema_c)
        new_growth_g_m2 = max(0.0, net_dry_matter_g_m2_hour)
        fruit_dm_increment = new_growth_g_m2 * fruit_fraction * f_fruit_set

        new_fruit_dm = state.fruit_dry_matter_g_m2 + fruit_dm_increment
        new_fruit_fresh_yield_kg_m2 = new_fruit_dm / self.params.dry_matter_content_fruit / 1000.0

        new_state = CropState(
            days_after_planting=state.days_after_planting + dt_hours / 24.0,
            recent_temp_ema_c=new_temp_ema_c,
            leaf_area_index=lai,
            standing_dry_matter_g_m2=new_standing_dm,
            fruit_dry_matter_g_m2=new_fruit_dm,
            fruit_fresh_yield_kg_m2=new_fruit_fresh_yield_kg_m2,
            respiration_reference_g_m2=new_respiration_reference,
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
            fruit_set_fraction=f_fruit_set,
        )
