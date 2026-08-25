"""Parameter schema for the greenhouse digital twin.

All physical/operational parameters of a specific greenhouse live here.
Loading a YAML config produces a validated GreenhouseParams instance —
this is the single "paramaterizable" surface of the twin: to model a
different greenhouse, only the YAML changes, not the code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml


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
    # simplification. Sourced to comparable real systems, not this specific (not-yet-installed)
    # unit: a commercial greenhouse dehumidifier (DryGair DG-12) removes up to 48 kg/hour, and a
    # semi-closed greenhouse cooling/dehumidification system was measured removing ~75 kg/hour --
    # 75 sits at the upper end of that range, appropriate for a system this greenhouse's size
    # (~5000 m2). See docs/assumptions/climate-control.md and
    # docs/papers/greenhouse-dehumidification-capacity.md.
    dehumidification_capacity_kg_water_per_hour: float = 75.0
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

    def is_daytime(self, hour: int) -> bool:
        return self.day_start_hour <= hour < self.day_end_hour

    def heating_setpoint(self, hour: int) -> float:
        return self.heating_setpoint_day_c if self.is_daytime(hour) else self.heating_setpoint_night_c


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

    def __post_init__(self) -> None:
        if self.density_plants_per_m2 <= 0:
            raise ValueError("density_plants_per_m2 must be > 0")
        if self.reference_density_plants_per_m2 <= 0:
            raise ValueError("reference_density_plants_per_m2 must be > 0")
        if self.lai_max <= 0:
            raise ValueError("lai_max must be > 0")
        if not 0 < self.dry_matter_content_fruit < 1:
            raise ValueError("dry_matter_content_fruit must be in (0, 1)")


@dataclass
class HydroponicParams:
    system_type: str = "NFT"  # flag only in v1; not modeled in depth yet


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
    duration_days: int = 120
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
