"""Parameter schema for the greenhouse digital twin.

All physical/operational parameters of a specific greenhouse live here.
Loading a YAML config produces a validated GreenhouseParams instance —
this is the single "paramaterizable" surface of the twin: to model a
different greenhouse, only the YAML changes, not the code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from pathlib import Path

import yaml


class ClimatePhase(Enum):
    """Crop growth phase used to make climate_control setpoints phase-aware (see
    docs/plans/2026-08-31-phase-aware-climate-design.md). Boundaries are derived from
    CropParams.fruiting_start_days/fruiting_ramp_days (twin/crop_model.py's crop_growth_phase())
    -- not a second, independently-configured phase schedule.
    """

    VEGETATIVE = "vegetative"
    RAMP_UP = "ramp_up"
    FULL_FRUITING = "full_fruiting"


@dataclass
class GeometryParams:
    area_m2: float
    height_m: float
    cover_u_value_w_m2k: float
    cover_transmissivity: float
    cover_area_factor: float = 1.3  # roof+walls surface area as a multiple of floor area

    def __post_init__(self) -> None:
        if self.area_m2 <= 0:
            raise ValueError("area_m2 must be > 0")
        if self.height_m <= 0:
            raise ValueError("height_m must be > 0")
        if not 0 < self.cover_transmissivity <= 1:
            raise ValueError("cover_transmissivity must be in (0, 1]")
        if self.cover_u_value_w_m2k <= 0:
            raise ValueError("cover_u_value_w_m2k must be > 0")

    @property
    def volume_m3(self) -> float:
        return self.area_m2 * self.height_m

    @property
    def cover_area_m2(self) -> float:
        return self.area_m2 * self.cover_area_factor


@dataclass
class CHPParams:
    """Combined Heat and Power unit.

    The electrical output runs at a FIXED rate (grid-driven, not
    greenhouse-driven) — so heat and CO2 output are fixed too. Any surplus
    heat/CO2 the greenhouse doesn't need is dumped/vented, never throttled.
    """

    electric_power_kw: float
    heat_to_power_ratio: float  # recoverable thermal kW per electrical kW
    co2_kg_per_kwh_elec: float  # flue-gas CO2 recovered, per kWh of electrical output

    def __post_init__(self) -> None:
        if self.electric_power_kw <= 0:
            raise ValueError("electric_power_kw must be > 0")
        if self.heat_to_power_ratio < 0:
            raise ValueError("heat_to_power_ratio must be >= 0")
        if self.co2_kg_per_kwh_elec < 0:
            raise ValueError("co2_kg_per_kwh_elec must be >= 0")

    @property
    def heat_available_kw(self) -> float:
        """Constant thermal output available to the greenhouse (kW)."""
        return self.electric_power_kw * self.heat_to_power_ratio

    @property
    def co2_available_kg_per_hour(self) -> float:
        """Constant CO2 output available to the greenhouse (kg/h)."""
        return self.electric_power_kw * self.co2_kg_per_kwh_elec


@dataclass
class ClimateControlParams:
    # These two are the VEGETATIVE-phase target (see the phase-delta fields below) -- previously
    # the single flat setpoint for the whole season, before phase-aware climate control
    # (2026-08-31, see docs/plans/2026-08-31-phase-aware-climate-design.md).
    heating_setpoint_day_c: float
    heating_setpoint_night_c: float
    day_start_hour: int = 6
    day_end_hour: int = 20
    vent_temp_margin_c: float = 2.0  # venting kicks in this many degrees above the heating setpoint
    vent_max_ach: float = 15.0  # max air changes per hour under mechanical/natural ventilation
    vent_min_ach: float = 0.5  # baseline leakage air exchange, always present
    co2_setpoint_day_ppm: float = 900.0
    co2_ambient_ppm: float = 420.0
    effective_heat_capacity_j_m2k: float = 40_000.0  # lumped thermal mass per m2 floor area
    # SOURCED: fraction cut from BOTH transmission heat loss and solar gain when the thermal
    # screen is deployed -- real product spec (Ludvig Svensson-style PH55, "55% shading, ~55%
    # energy saving") from a real vendor quote for this greenhouse: same fabric, same ~55% figure
    # for both effects. See docs/papers/geothermiki-s192g-quote.md. Deployment itself is fully
    # automatic (twin/climate_model.py: GreenhouseClimateModel._screen_should_deploy) -- not a
    # user-adjustable schedule; see climate-control.md for the 3-criteria control logic.
    screen_energy_saving_fraction: float = 0.55
    # PLACEHOLDER: safety margin for the screen's "CHP can't keep up" trigger -- deploys (if net
    # beneficial once its solar-blocking cost is weighed in) once required heating power exceeds
    # this fraction of the CHP's fixed heat output, rather than waiting for 100% (which would
    # mean the setpoint is already being missed before the screen even reacts). An engineering
    # safety-margin choice, not from a specific literature source. See climate-control.md.
    chp_heat_margin_fraction: float = 0.9
    # PLACEHOLDER: cover surface temperature as a fraction of the way from outdoor to indoor air
    # temperature -- a thin PE film has little thermal resistance of its own compared to the air
    # boundary layers on each side, so its surface sits closer to outdoor temperature than indoor.
    # Not individually sourced; see docs/assumptions/climate-control.md.
    cover_surface_temp_fraction: float = 0.3
    # PLACEHOLDER: effective relaxation rate (1/hour) at which bulk air moisture is pulled toward
    # what the cold cover surface allows, once condensation conditions are met. Engineering
    # approximation, not a measured mass-transfer coefficient.
    condensation_rate_constant: float = 2.0
    # SOURCED: RH ceiling the (idealized) active dehumidification system targets. Literature range
    # for greenhouse tomato is 60-85% (day 80-85%, night 65-75%), but 70% is specifically cited as
    # the optimum for pollination (>80% pollen clumps together; <60% stigma dries out) -- used as
    # the single setpoint. See docs/assumptions/climate-control.md.
    dehumidification_setpoint_pct: float = 70.0
    # PLACEHOLDER: real removal capacity of the active dehumidification system (represents the
    # real quote's OptiClima cooling/dehumidification panels -- no capacity spec was in that
    # quote). Added 2026-08-25 to replace the earlier "unconstrained, always reaches setpoint"
    # simplification. Revised same day: an initial 75 kg/hour estimate (sourced to a small
    # portable unit, DryGair DG-12) turned out to be a scale mismatch -- that unit covers
    # ~3,700 m2, well under this greenhouse's 5000 m2, and the quote actually describes a full
    # "semi-closed greenhouse climate system" (OptiClima, EUR195,000), not a bolt-on portable
    # dehumidifier. Rescaled from a semi-closed greenhouse *cooling capacity* benchmark instead
    # (350 W/m2, mid-range of a 150-700 W/m2 reported span) x 5000 m2 x an assumed ~30% of that
    # cooling capacity going to latent (moisture-condensing) load rather than sensible heat
    # removal -- a typical order of magnitude for a dehumidification-focused duty cycle, not a
    # measured split for this system -- giving ~770 kg/hour. See
    # docs/assumptions/climate-control.md and docs/papers/greenhouse-dehumidification-capacity.md.
    dehumidification_capacity_kg_water_per_hour: float = 771.0
    # Initial config choice, off by default: does this greenhouse have a fan-and-pad
    # evaporative cooling system? When enabled, air drawn in by active ventilation is
    # first pre-cooled (and humidified) by passing through wet pads before entering the
    # greenhouse, letting ventilation cool below the raw outdoor dry-bulb temperature.
    # See docs/assumptions/climate-control.md and docs/papers/geothermiki-s192g-quote.md (the
    # vendor quote's "cooling panels").
    fan_pad_cooling_enabled: bool = False
    # SOURCED: fraction of the way from outdoor dry-bulb conditions to saturation at the
    # outdoor wet-bulb temperature that pad-cooled air reaches. UF/IFAS Extension (Fan and
    # Pad Greenhouse Evaporative Cooling Systems, CIR1135/AE069) cites up to 85% for a
    # well-designed, well-maintained system; Alabama Extension gives 70-85% for well-
    # maintained systems generally. 0.80 is a representative value within that range. Only
    # used when fan_pad_cooling_enabled is True. See docs/assumptions/climate-control.md.
    fan_pad_efficiency: float = 0.80
    # SOURCED: electrical energy per kg of water actually removed by the active
    # dehumidification system -- 0.22 kWh/kg is the DryGair DG-12's own published
    # efficiency spec (9.55 kW drawn, ~45 kg/hour removed -> ~4.5 kg/kWh -> ~0.22
    # kWh/kg; https://drygair.com/dehumidifiers/dg-12-50hz-standard/). Reused here even
    # though the DG-12's *capacity* was rejected as a scale mismatch for this greenhouse
    # (see dehumidification_capacity_kg_water_per_hour above) -- kWh-per-kg is a property
    # of the dehumidification technology (refrigerant-cycle moisture removal), not of the
    # unit's physical size, so it transfers independently of that capacity issue. See
    # docs/papers/greenhouse-electricity-consumption.md.
    dehumidification_specific_power_kwh_per_kg: float = 0.22
    # SOURCED: electrical power per unit of active (above-baseline) ventilation airflow,
    # engaged only when fan_pad_cooling_enabled and ventilation is ramped above
    # vent_min_ach -- passive roof-vent leakage at vent_min_ach is naturally driven
    # (buoyancy/wind through motorized vents) and draws negligible power, so this only
    # prices the fan-pad system's forced-air fans. 0.03 W per (m3/h) is the middle of a
    # 0.025-0.045 W/(m3/h) range measured across real greenhouse ventilation fans (older
    # vs. newer energy-efficient models); see Vostermans, "Save Energy in Your Greenhouse
    # with Efficient Fan Choices" (https://www.vostermans.com/ventilation/blog/how-can-i-save-energy-in-a-greenhouse).
    # See docs/papers/greenhouse-electricity-consumption.md.
    ventilation_specific_fan_power_w_per_m3h: float = 0.03
    # PLACEHOLDER: combined electrical power of this greenhouse's horizontal-airflow (HAF)
    # recirculation fan bank (the vendor quote's ACF21 units, 508mm/20", 5,400 m3/h each --
    # a real "air recirculation" cost line item, but no fan count or unit spec). Estimated
    # from the quote's own geometry: one row of fans per bay (5 bays, matching the quote's
    # own racetrack fan-layout diagram) x ~7 fans/row (100m length / ~14m real-world HAF
    # spacing guidance, "one fan every 40-50 ft") = 35 fans x 5,400 m3/h x an assumed
    # 0.025 W/(m3/h) specific power (real 20" HAF fans run ~0.017-0.04 W/(m3/h), similar
    # efficiency range to exhaust fans but slightly better since HAF works against much
    # lower static pressure) ~= 4.7 kW total when running. Not a real fan count/spec for
    # this installation. See docs/papers/greenhouse-electricity-consumption.md.
    recirculation_fan_power_kw: float = 4.7
    # -- Phase-aware climate control, temperature only (2026-08-31, first pass -- see
    # docs/plans/2026-08-31-phase-aware-climate-design.md). heating_setpoint_day_c/night_c above
    # are the vegetative-phase target; each later phase's actual target is that baseline plus its
    # own delta here. SOURCED: general greenhouse-tomato grower guidance repeatedly cites the
    # flowering/fruit-set/full-fruiting period as running ~2C warmer (both day and night) than
    # the vegetative stage -- ramp_up (the fruit-set ramp itself) gets the same delta as
    # full_fruiting since the cited guidance doesn't distinguish a separate intermediate target
    # for that window. See docs/assumptions/climate-control.md.
    ramp_up_heating_setpoint_day_delta_c: float = 2.0
    ramp_up_heating_setpoint_night_delta_c: float = 2.0
    full_fruiting_heating_setpoint_day_delta_c: float = 2.0
    full_fruiting_heating_setpoint_night_delta_c: float = 2.0

    def __post_init__(self) -> None:
        if not 0 <= self.day_start_hour < 24 or not 0 <= self.day_end_hour <= 24:
            raise ValueError("day_start_hour/day_end_hour must be within [0, 24]")
        if self.heating_setpoint_day_c < self.heating_setpoint_night_c:
            raise ValueError("heating_setpoint_day_c must be >= heating_setpoint_night_c")
        if self.co2_ambient_ppm < 0:
            raise ValueError("co2_ambient_ppm must be >= 0")
        if self.co2_setpoint_day_ppm < self.co2_ambient_ppm:
            raise ValueError("co2_setpoint_day_ppm must be >= co2_ambient_ppm")
        if not 0 < self.chp_heat_margin_fraction <= 1:
            raise ValueError("chp_heat_margin_fraction must be in (0, 1]")
        if self.vent_max_ach < self.vent_min_ach:
            raise ValueError("vent_max_ach must be >= vent_min_ach")
        if not 0 < self.fan_pad_efficiency <= 1:
            raise ValueError("fan_pad_efficiency must be in (0, 1]")
        if self.dehumidification_capacity_kg_water_per_hour <= 0:
            raise ValueError("dehumidification_capacity_kg_water_per_hour must be > 0")
        if self.effective_heat_capacity_j_m2k <= 0:
            raise ValueError("effective_heat_capacity_j_m2k must be > 0")
        if not 0 <= self.cover_surface_temp_fraction <= 1:
            raise ValueError("cover_surface_temp_fraction must be in [0, 1]")
        if self.condensation_rate_constant < 0:
            raise ValueError("condensation_rate_constant must be >= 0")
        if not 0 < self.dehumidification_setpoint_pct <= 100:
            raise ValueError("dehumidification_setpoint_pct must be in (0, 100]")
        if not 0 <= self.screen_energy_saving_fraction < 1:
            raise ValueError("screen_energy_saving_fraction must be in [0, 1)")
        if self.dehumidification_specific_power_kwh_per_kg <= 0:
            raise ValueError("dehumidification_specific_power_kwh_per_kg must be > 0")
        if self.ventilation_specific_fan_power_w_per_m3h <= 0:
            raise ValueError("ventilation_specific_fan_power_w_per_m3h must be > 0")
        if self.recirculation_fan_power_kw <= 0:
            raise ValueError("recirculation_fan_power_kw must be > 0")

    def is_daytime(self, hour: int) -> bool:
        return self.day_start_hour <= hour < self.day_end_hour

    def heating_setpoint(self, hour: int, phase: ClimatePhase) -> float:
        base = self.heating_setpoint_day_c if self.is_daytime(hour) else self.heating_setpoint_night_c
        if phase is ClimatePhase.VEGETATIVE:
            return base
        if phase is ClimatePhase.RAMP_UP:
            delta = self.ramp_up_heating_setpoint_day_delta_c if self.is_daytime(hour) else self.ramp_up_heating_setpoint_night_delta_c
        else:
            delta = (
                self.full_fruiting_heating_setpoint_day_delta_c
                if self.is_daytime(hour)
                else self.full_fruiting_heating_setpoint_night_delta_c
            )
        return base + delta


@dataclass
class CropParams:
    variety: str
    planting_date: date
    density_plants_per_m2: float
    # Density lai_max was calibrated at. SOURCED — default matches standard
    # commercial single-stem high-wire greenhouse tomato practice (2.3-2.5
    # plants/m2; Peet & Welles, Greenhouse Tomato Production; VT Extension
    # SPES-474). Full audit: docs/assumptions/crop-model.md
    reference_density_plants_per_m2: float = 2.5
    lai_max: float = 3.5
    lai_ramp_days: float = 60.0  # days after planting to reach ~lai_max
    fruiting_start_days: float = 35.0  # days after planting before fruit partitioning begins
    fruiting_ramp_days: float = 20.0  # days to ramp from 0 to full fruit partition fraction
    # SOURCED: raised from an earlier 0.6 placeholder to match TOMGRO literature
    # (Bertin & Gary, 1993 calibration/validation for indeterminate greenhouse
    # tomato), which reports 80-90% of dry-matter gain to fruit at peak fruiting.
    # Full audit: docs/assumptions/crop-model.md
    fruit_partition_fraction_max: float = 0.85
    dry_matter_content_fruit: float = 0.055  # fraction dry matter of fresh tomato fruit
    # SOURCED: target fresh fruit weight for this greenhouse's chosen variety class (EYRE RZ
    # F1, Rijk Zwaan -- 230-280g, midpoint used). Not yet an input to the crop model's own
    # growth physics (that's still driven by fruit_partition_fraction_max / dry matter
    # accumulation) -- used as a reporting/derivation constant, converting the model's
    # continuous fruit dry-matter output into fruit-count-based metrics (trusses/week) that
    # match how a real grower actually tracks this crop. See
    # docs/papers/tomato-variety-selection-northern-greece.md.
    target_fruit_weight_g: float = 255.0
    # SOURCED: fruits per truss, generic class-level figure for beef/TOV-type indeterminate
    # greenhouse tomato (4-6 fruits/truss cited across multiple sources) -- not an EYRE RZ F1
    # datasheet figure (not publicly available), a class-level benchmark. Used alongside
    # target_fruit_weight_g to derive truss-rate metrics from the model's cumulative fruit
    # yield. See docs/papers/tomato-variety-selection-northern-greece.md.
    fruits_per_truss: float = 5.0
    # Growing system: 1 = single-stem (the default this project's density/reference-density
    # figures were sourced against -- Peet & Welles, VT Extension SPES-474), 2 = two-stem
    # (e.g. Belladona F1, checked during variety selection -- see
    # docs/papers/tomato-variety-selection-northern-greece.md). Feeds twin/crop_model.py's
    # canopy/LAI density scaling and this API's truss-rate derivation as an effective
    # stems/m2 = density_plants_per_m2 * stems_per_plant, since canopy size and truss
    # production scale with total stem count, not plant count. SITE-SPECIFIC: set to match
    # whichever real variety is chosen; 1 for the current EYRE RZ F1-class default.
    stems_per_plant: int = 1
    # SOURCED: bell-shaped photosynthesis temperature response thresholds (T_MIN, T_OPT,
    # T_MAX), moved here from twin/crop_model.py module constants (2026-08-26) so a
    # different variety's temperature tolerance is a config value, not a code change. Same
    # defaults as before -- no behavior change. See docs/assumptions/crop-model.md.
    photosynthesis_t_min_c: float = 10.0
    photosynthesis_t_opt_c: float = 27.0
    photosynthesis_t_max_c: float = 35.0
    # SOURCED: fruit-set temperature tolerance thresholds -- much narrower than the
    # photosynthesis response above (pollen viability/fruit set is far more temperature-
    # sensitive). Moved from twin/crop_model.py module constants (2026-08-26) for the same
    # reason -- this is exactly the trait that differs meaningfully between real varieties
    # (e.g. Merlice F1's "very good fruit set at high temperatures" vs. this default, checked
    # during variety selection). Same defaults as before -- no behavior change.
    fruit_set_t_min_c: float = 12.0
    fruit_set_t_opt_c: float = 18.0
    fruit_set_t_max_c: float = 24.0
    # SOURCED: Beer-Lambert canopy light extinction coefficient, reported 0.7-0.9 for
    # high-wire tomato canopies -- varies somewhat with a variety's leaf habit/canopy
    # architecture. Moved from a twin/crop_model.py module constant (2026-08-26). Same
    # default as before -- no behavior change.
    canopy_light_extinction_coeff: float = 0.75
    # PLACEHOLDER: maintenance respiration as a fraction of standing biomass per day --
    # plant vigor (and therefore respiration load) varies somewhat by variety. Moved from a
    # twin/crop_model.py module constant (2026-08-26). Same default as before -- no behavior
    # change.
    maintenance_respiration_fraction_per_day: float = 0.015

    def __post_init__(self) -> None:
        if self.density_plants_per_m2 <= 0:
            raise ValueError("density_plants_per_m2 must be > 0")
        if self.reference_density_plants_per_m2 <= 0:
            raise ValueError("reference_density_plants_per_m2 must be > 0")
        if self.lai_max <= 0:
            raise ValueError("lai_max must be > 0")
        if not 0 < self.dry_matter_content_fruit < 1:
            raise ValueError("dry_matter_content_fruit must be in (0, 1)")
        if self.target_fruit_weight_g <= 0:
            raise ValueError("target_fruit_weight_g must be > 0")
        if self.fruits_per_truss <= 0:
            raise ValueError("fruits_per_truss must be > 0")
        if self.stems_per_plant not in (1, 2):
            raise ValueError("stems_per_plant must be 1 (single-stem) or 2 (two-stem)")
        if not self.photosynthesis_t_min_c < self.photosynthesis_t_opt_c < self.photosynthesis_t_max_c:
            raise ValueError("photosynthesis_t_min_c < photosynthesis_t_opt_c < photosynthesis_t_max_c required")
        if not self.fruit_set_t_min_c < self.fruit_set_t_opt_c < self.fruit_set_t_max_c:
            raise ValueError("fruit_set_t_min_c < fruit_set_t_opt_c < fruit_set_t_max_c required")
        if self.canopy_light_extinction_coeff <= 0:
            raise ValueError("canopy_light_extinction_coeff must be > 0")
        if self.maintenance_respiration_fraction_per_day <= 0:
            raise ValueError("maintenance_respiration_fraction_per_day must be > 0")


@dataclass
class HydroponicParams:
    # SOURCED (corrected 2026-08-26): commercial greenhouse tomato is grown on drip-irrigated
    # substrate (rockwool/coco), not NFT -- NFT is common for leafy greens/lettuce, not
    # indeterminate high-wire tomato. See docs/papers/tomato-variety-selection-northern-greece.md
    # (real Northern Greece precedent) and docs/papers/geothermiki-s192g-quote.md (this project's
    # own vendor quote: Spagnol BravoJet EC/pH fertigation, not an NFT gutter system).
    system_type: str = "drip_substrate"
    substrate_type: str = "rockwool"  # descriptive only -- doesn't yet feed the physics
    ec_target_ms_cm: float = 3.0  # SOURCED: 2.0-3.5 mS/cm is the commonly cited range for
    # greenhouse tomato (see docs/papers/hydroponic-fertigation-level-a.md)
    ph_target: float = 6.0  # SOURCED: 5.5-6.5 optimal nutrient-availability range, same source
    drainage_target_fraction: float = 0.25  # SOURCED: 20-30% leaching fraction is standard
    # substrate-culture practice (flushes accumulated salts) -- see same source
    irrigation_pump_specific_power_kwh_per_m3: float = 0.28  # SOURCED (general drip-irrigation
    # average, not this specific pump) -- see docs/papers/hydroponic-fertigation-level-a.md
    fertilizer_g_per_l_per_ec_unit: float = 0.64  # PLACEHOLDER: generic EC-to-TDS conversion
    # factor, not a specific fertilizer blend's real dosing curve -- see same source

    # -- Level B: EC -> fruit dry-matter fraction (B1) --
    # SOURCED: low-EC baseline from a study comparing 2.3 dS/m vs. 5.0 dS/m hydroponic tomato.
    # See docs/assumptions/hydroponics.md ("Level B" section) for the derivation and source link.
    ec_dry_matter_reference_ms_cm: float = 2.3
    # SOURCED: midpoint of the study's observed 0.19-0.37 percentage-point dry-matter increase
    # per +1 mS/cm (expressed here as a fraction, i.e. 0.0028 = 0.28 percentage points).
    ec_dry_matter_slope_per_ms_cm: float = 0.0028

    # -- Level B: EC -> BER (Blossom End Rot) risk / nutrient deficiency -> marketable yield loss
    # (B2), continuous bell curve peaked at ec_optimal_ms_cm (revised 2026-08-29: an earlier
    # threshold+linear-ramp version had a *flat* zone between the BER and deficiency thresholds
    # with zero yield change across it -- caught by the user as unrealistic, since real trials show
    # yield varying continuously with a single peak, not a plateau. e.g. one study found the
    # highest tomato yield at EC 3 dS/m, rising continuously from 0, falling continuously above it.
    # See docs/assumptions/hydroponics.md.)
    # SOURCED: the study's peak-yield EC point; also the middle of the commonly-cited 2.0-3.5
    # mS/cm commercial target range (Level A above).
    ec_optimal_ms_cm: float = 3.0
    # PLACEHOLDER curvatures (mS/cm)^-2, chosen so the loss fraction at a specific EC roughly
    # matches the magnitude the previous threshold-based version used at the same point (a
    # continuity check, not a literature-quantified curvature) -- high side reaches 10% loss at
    # EC=4.5 (ec_optimal+1.5), low side reaches 15% loss at EC=1.0 (ec_optimal-2.0).
    ec_high_side_curvature_per_ms_cm2: float = 0.0444
    ec_low_side_curvature_per_ms_cm2: float = 0.0375
    ber_yield_loss_fraction_max: float = 0.35
    ec_deficiency_yield_loss_fraction_max: float = 0.50

    # -- Level B: pH -> nutrient availability -> marketable yield loss, continuous bell curve
    # peaked at ph_optimal (revised 2026-08-29 for the same reason as EC above -- a flat
    # 5.5-6.5 "sufficiency range" showed literally zero difference across that whole span, which
    # the user correctly flagged as implausible). SOURCED peak: a trial testing pH
    # 4.5/5.0/5.5/6.0/6.5 found the highest tomato yield specifically at pH 5.5 (not a flat
    # optimum across a range) -- outside it, specific nutrients become progressively less
    # chemically available to the plant even if present in solution (a real, well-documented
    # mechanism -- classic soilless-culture nutrient-availability charts). See
    # docs/assumptions/hydroponics.md.
    ph_optimal: float = 5.5
    # PLACEHOLDER curvature (pH unit)^-2: no quantified tomato-specific yield-loss-vs-pH-distance
    # figure was found, so this is chosen to reach the cap at 1.5 pH units from the peak.
    ph_curvature_per_ph_unit2: float = 0.0667
    # PLACEHOLDER: higher cap than any single damped-tier nutrient below, since pH gates the
    # availability of *all* nutrients simultaneously, not just one.
    ph_availability_penalty_cap_fraction: float = 0.15

    # -- Recipe "damped" tier: N, K, Mg, B -- real mechanism, deliberately small/capped magnitude.
    # Each nutrient's `_ppm` is the recipe's actual target concentration; `_min_optimal_ppm` /
    # `_max_optimal_ppm` is the sufficiency range within which it costs nothing. Ranges are
    # SOURCED (University of Arizona CEAC / University of Florida IFAS tomato formulas); the
    # penalty magnitude (`damped_nutrient_penalty_cap_fraction`) is PLACEHOLDER -- the mechanism
    # is real, the magnitude is a deliberate conservative guess. See docs/assumptions/hydroponics.md.
    n_ppm: float = 105.0
    n_min_optimal_ppm: float = 60.0
    n_max_optimal_ppm: float = 150.0
    k_ppm: float = 300.0
    k_min_optimal_ppm: float = 199.0
    k_max_optimal_ppm: float = 400.0
    mg_ppm: float = 65.0  # SOURCED: CEAC Arizona tomato formula (constant across all 3 recipe variants)
    mg_min_optimal_ppm: float = 45.0
    mg_max_optimal_ppm: float = 70.0
    b_ppm: float = 0.40  # SOURCED: CEAC Arizona micronutrient formula
    b_min_optimal_ppm: float = 0.30
    b_max_optimal_ppm: float = 0.50
    # PLACEHOLDER: each of the four damped-tier nutrients is capped at this much individual yield
    # penalty when its ppm is a full sufficiency-range-width beyond the range boundary (a linear
    # ramp from 0 at the boundary to this cap at that distance, capped beyond it).
    damped_nutrient_penalty_cap_fraction: float = 0.02
    # PLACEHOLDER: floor on the combined multiplicative effect of all four damped-tier nutrients
    # together, so the whole tier can never produce an unrealistically large swing.
    recipe_adequacy_multiplier_min: float = 0.85

    # -- Recipe "informational" tier: P, S, Fe, Mn, Zn, Cu, Mo -- displayed for reference only,
    # not read by any physics (same treatment as the frontend's existing pollination block).
    # SOURCED (CEAC Arizona formula, cross-checked against Florida IFAS where noted).
    p_ppm: float = 62.0
    s_ppm: float = 110.0  # CEAC: ~102-121 ppm across its 3 recipe variants, ~110 used as midpoint
    fe_ppm: float = 2.5
    mn_ppm: float = 0.55  # CEAC 0.55; Florida IFAS cites 0.62 -- sources disagree, CEAC used here
    zn_ppm: float = 0.33  # CEAC 0.33; Florida IFAS cites 0.09 -- notable disagreement, CEAC used
    # here since it's internally consistent with the other CEAC-sourced values above
    cu_ppm: float = 0.05
    mo_ppm: float = 0.05

    def __post_init__(self) -> None:
        if self.ec_target_ms_cm <= 0:
            raise ValueError("ec_target_ms_cm must be > 0")
        if not 0 < self.ph_target < 14:
            raise ValueError("ph_target must be in (0, 14)")
        if not 0 <= self.drainage_target_fraction < 1:
            raise ValueError("drainage_target_fraction must be in [0, 1)")
        if self.irrigation_pump_specific_power_kwh_per_m3 <= 0:
            raise ValueError("irrigation_pump_specific_power_kwh_per_m3 must be > 0")
        if self.fertilizer_g_per_l_per_ec_unit <= 0:
            raise ValueError("fertilizer_g_per_l_per_ec_unit must be > 0")
        if self.ec_dry_matter_reference_ms_cm <= 0:
            raise ValueError("ec_dry_matter_reference_ms_cm must be > 0")
        if self.ec_optimal_ms_cm <= 0:
            raise ValueError("ec_optimal_ms_cm must be > 0")
        if self.ec_high_side_curvature_per_ms_cm2 < 0:
            raise ValueError("ec_high_side_curvature_per_ms_cm2 must be >= 0")
        if self.ec_low_side_curvature_per_ms_cm2 < 0:
            raise ValueError("ec_low_side_curvature_per_ms_cm2 must be >= 0")
        if not 0 < self.ber_yield_loss_fraction_max <= 1:
            raise ValueError("ber_yield_loss_fraction_max must be in (0, 1]")
        if not 0 < self.ec_deficiency_yield_loss_fraction_max <= 1:
            raise ValueError("ec_deficiency_yield_loss_fraction_max must be in (0, 1]")
        if not 0 < self.ph_optimal < 14:
            raise ValueError("ph_optimal must be in (0, 14)")
        if self.ph_curvature_per_ph_unit2 < 0:
            raise ValueError("ph_curvature_per_ph_unit2 must be >= 0")
        if not 0 <= self.ph_availability_penalty_cap_fraction <= 1:
            raise ValueError("ph_availability_penalty_cap_fraction must be in [0, 1]")
        for label, lo, hi in (
            ("n", self.n_min_optimal_ppm, self.n_max_optimal_ppm),
            ("k", self.k_min_optimal_ppm, self.k_max_optimal_ppm),
            ("mg", self.mg_min_optimal_ppm, self.mg_max_optimal_ppm),
            ("b", self.b_min_optimal_ppm, self.b_max_optimal_ppm),
        ):
            if lo <= 0:
                raise ValueError(f"{label}_min_optimal_ppm must be > 0")
            if hi <= lo:
                raise ValueError(f"{label}_max_optimal_ppm must be > {label}_min_optimal_ppm")
        if not 0 <= self.damped_nutrient_penalty_cap_fraction <= 1:
            raise ValueError("damped_nutrient_penalty_cap_fraction must be in [0, 1]")
        if not 0 < self.recipe_adequacy_multiplier_min <= 1:
            raise ValueError("recipe_adequacy_multiplier_min must be in (0, 1]")

    @property
    def effective_dry_matter_content_fruit(self) -> float:
        """Level B1: EC-adjusted fruit dry-matter fraction (denser/smaller fruit at higher EC).

        `dry_matter_content_fruit` (CropParams) is a constant divisor throughout the crop
        model's run, so scaling it by this factor and dividing final yield by the ratio is
        mathematically equivalent to having used the EC-adjusted fraction from hour 1 -- no
        hourly-loop change needed. See docs/assumptions/hydroponics.md ("Level B").
        """
        return 1.0 + self.ec_dry_matter_slope_per_ms_cm * (self.ec_target_ms_cm - self.ec_dry_matter_reference_ms_cm)

    @property
    def ber_yield_loss_fraction(self) -> float:
        """Level B2: EC-driven BER (Blossom End Rot) marketable-yield loss, a continuous
        parabola on the high-EC side of `ec_optimal_ms_cm` (0 exactly at the peak, growing with
        the square of the distance above it) -- see docs/assumptions/hydroponics.md for why this
        replaced an earlier flat-threshold version.
        """
        if self.ec_target_ms_cm <= self.ec_optimal_ms_cm:
            return 0.0
        excess = self.ec_target_ms_cm - self.ec_optimal_ms_cm
        return min(self.ber_yield_loss_fraction_max, self.ec_high_side_curvature_per_ms_cm2 * excess * excess)

    @property
    def ec_deficiency_yield_loss_fraction(self) -> float:
        """Level B, low-EC side: nutrient-deficiency yield loss, the mirror-image parabola below
        `ec_optimal_ms_cm` -- together with ber_yield_loss_fraction this makes the full EC/yield
        response a single continuous bell peaked at ec_optimal_ms_cm, not a flat-then-ramp shape.
        """
        if self.ec_target_ms_cm >= self.ec_optimal_ms_cm:
            return 0.0
        deficit = self.ec_optimal_ms_cm - self.ec_target_ms_cm
        return min(self.ec_deficiency_yield_loss_fraction_max, self.ec_low_side_curvature_per_ms_cm2 * deficit * deficit)

    def _nutrient_penalty(self, value: float, min_optimal: float, max_optimal: float) -> float:
        """Damped recipe tier: 0 inside [min_optimal, max_optimal], ramping linearly to
        `damped_nutrient_penalty_cap_fraction` once `value` is a full range-width beyond
        whichever boundary it's outside of, capped there. Unlike EC/pH (continuous environmental
        dials with a literature-documented single yield peak, see ber_yield_loss_fraction /
        ph_availability_multiplier above), N/K/Mg/B genuinely have a flat sufficiency range in
        real agronomy -- a concentration band within which uptake is adequate -- so a flat zone
        here is not the same modeling gap that EC/pH had.
        """
        if min_optimal <= value <= max_optimal:
            return 0.0
        range_width = max_optimal - min_optimal
        distance = min_optimal - value if value < min_optimal else value - max_optimal
        return min(
            self.damped_nutrient_penalty_cap_fraction, self.damped_nutrient_penalty_cap_fraction * distance / range_width
        )

    @property
    def ph_availability_multiplier(self) -> float:
        """Level B: pH-driven nutrient-availability yield loss, a continuous parabola peaked at
        `ph_optimal` (applied as its own factor, distinct from recipe_adequacy_multiplier, since
        pH gates availability of every nutrient at once, not one specific concentration). See
        docs/assumptions/hydroponics.md for why this replaced an earlier flat-range version.
        """
        distance = self.ph_target - self.ph_optimal
        loss = min(self.ph_availability_penalty_cap_fraction, self.ph_curvature_per_ph_unit2 * distance * distance)
        return 1.0 - loss

    @property
    def recipe_adequacy_multiplier(self) -> float:
        """Damped recipe tier: combined multiplicative yield effect of N/K/Mg/B, each
        individually capped and the combination itself floored at
        `recipe_adequacy_multiplier_min` so the tier can never swing yield unrealistically far.
        """
        combined = (
            (1.0 - self._nutrient_penalty(self.n_ppm, self.n_min_optimal_ppm, self.n_max_optimal_ppm))
            * (1.0 - self._nutrient_penalty(self.k_ppm, self.k_min_optimal_ppm, self.k_max_optimal_ppm))
            * (1.0 - self._nutrient_penalty(self.mg_ppm, self.mg_min_optimal_ppm, self.mg_max_optimal_ppm))
            * (1.0 - self._nutrient_penalty(self.b_ppm, self.b_min_optimal_ppm, self.b_max_optimal_ppm))
        )
        return max(self.recipe_adequacy_multiplier_min, combined)


@dataclass
class WeatherParams:
    source: str = "synthetic"  # "synthetic", "csv" (exact-date historical), or "csv_typical_year"
    csv_path: str | None = None
    latitude_deg: float = 37.9  # default: Athens, Greece
    mean_annual_temp_c: float = 18.0
    seasonal_amplitude_c: float = 9.0
    diurnal_amplitude_c: float = 6.0
    peak_solar_w_m2: float = 850.0


@dataclass
class SimulationParams:
    start_date: date
    duration_days: int = 330  # SOURCED: real commercial indeterminate greenhouse tomato cropping
    # cycles run ~10-11 months before replanting. See docs/assumptions/crop-model.md.
    timestep_hours: float = 1.0

    def __post_init__(self) -> None:
        if self.duration_days <= 0:
            raise ValueError("duration_days must be > 0")
        if self.timestep_hours <= 0:
            raise ValueError("timestep_hours must be > 0")


@dataclass
class GreenhouseParams:
    name: str
    geometry: GeometryParams
    chp: CHPParams
    climate_control: ClimateControlParams
    crop: CropParams
    simulation: SimulationParams
    hydroponic: HydroponicParams = field(default_factory=HydroponicParams)
    weather: WeatherParams = field(default_factory=WeatherParams)

    @staticmethod
    def from_dict(raw: dict) -> "GreenhouseParams":
        return GreenhouseParams(
            name=raw["name"],
            geometry=GeometryParams(**raw["geometry"]),
            chp=CHPParams(**raw["chp"]),
            climate_control=ClimateControlParams(**raw.get("climate_control", {})),
            crop=CropParams(**raw["crop"]),
            simulation=SimulationParams(**raw["simulation"]),
            hydroponic=HydroponicParams(**raw.get("hydroponic", {})),
            weather=WeatherParams(**raw.get("weather", {})),
        )

    @staticmethod
    def from_yaml(path: str | Path) -> "GreenhouseParams":
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        return GreenhouseParams.from_dict(raw)
