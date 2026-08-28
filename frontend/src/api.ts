function detectApiBase(): string {
  if (import.meta.env.VITE_API_BASE) return import.meta.env.VITE_API_BASE;

  // Auto-detect the backend on GitHub Codespaces / Gitpod-style forwarded
  // preview URLs, e.g. https://<name>-5173.app.github.dev -> ...-8123.app.github.dev
  const { hostname, protocol } = window.location;
  const match = hostname.match(/^(.*)-5173(\.app\.github\.dev)$/);
  if (match) {
    return `${protocol}//${match[1]}-8123${match[2]}`;
  }

  return "http://127.0.0.1:8123";
}

const API_BASE = detectApiBase();

export interface GreenhouseConfig {
  name: string;
  geometry: {
    area_m2: number;
    height_m: number;
    cover_u_value_w_m2k: number;
    cover_transmissivity: number;
  };
  chp: { electric_power_kw: number; heat_to_power_ratio: number; co2_kg_per_kwh_elec: number };
  crop: {
    variety: string;
    planting_date: string;
    density_plants_per_m2: number;
    fruiting_start_days: number;
    fruiting_ramp_days: number;
    target_fruit_weight_g: number;
    fruits_per_truss: number;
    stems_per_plant: number;
    [key: string]: unknown;
  };
  hydroponic: {
    system_type: string;
    substrate_type: string;
    ec_target_ms_cm: number;
    ph_target: number;
    drainage_target_fraction: number;
    /** Damped recipe tier (hydroponics.md "Level B"): actual recipe ppm + sufficiency range. */
    n_ppm: number;
    n_min_optimal_ppm: number;
    n_max_optimal_ppm: number;
    k_ppm: number;
    k_min_optimal_ppm: number;
    k_max_optimal_ppm: number;
    mg_ppm: number;
    mg_min_optimal_ppm: number;
    mg_max_optimal_ppm: number;
    b_ppm: number;
    b_min_optimal_ppm: number;
    b_max_optimal_ppm: number;
    /** Informational recipe tier -- reference only, no model effect. */
    p_ppm: number;
    s_ppm: number;
    fe_ppm: number;
    mn_ppm: number;
    zn_ppm: number;
    cu_ppm: number;
    mo_ppm: number;
    [key: string]: unknown;
  };
  simulation: { start_date: string; duration_days: number; timestep_hours: number };
  climate_control: {
    heating_setpoint_day_c: number;
    heating_setpoint_night_c: number;
    co2_setpoint_day_ppm: number;
    screen_energy_saving_fraction: number;
    dehumidification_setpoint_pct: number;
    fan_pad_cooling_enabled: boolean;
    recirculation_fan_power_kw: number;
    [key: string]: unknown;
  };
  weather: { source: string; latitude_deg: number; [key: string]: unknown };
  [key: string]: unknown;
}

export interface DailyPoint {
  date: string;
  temp_in_c: number;
  temp_out_c: number;
  /** Daytime-only average (day_start_hour-day_end_hour) — the CO2 dosing target only applies
   * during the day, so a full 24h mean would misleadingly blend it with the night's
   * intentionally-lower ambient target. */
  co2_in_ppm: number;
  rh_in_pct: number;
  vpd_kpa: number;
  fruit_fresh_yield_kg_m2: number;
  /** Daily-average thermal power draw (kW), normalized per hour — not a daily total. */
  heat_used_kw: number;
  /** Hours that day the thermal screen was deployed (fully automatic — see backend). */
  screen_closed_hours: number;
  /** Hours that day fan-pad cooling was engaged (fully automatic — see backend). */
  fan_pad_active_hours: number;
  /** Daily-average electric power (kW) drawn by active dehumidification. */
  dehumidification_elec_kw: number;
  /** Daily-average electric power (kW) drawn by the fan-pad system's forced-air fans. */
  ventilation_elec_kw: number;
  /** Daily-average electric power (kW) drawn by the recirculation (HAF) fan bank. */
  recirculation_elec_kw: number;
  /** Daily-average electric power (kW) drawn by the fertigation dosing pump. */
  fertigation_elec_kw: number;
  /** Daily total irrigation water volume (liters), derived from the crop's transpiration
   * demand plus the drainage/leaching fraction (hydroponics.md Level A). */
  irrigation_water_l_day: number;
  /** Daily total drained/leached water volume (liters) -- irrigation minus what the crop
   * actually transpired. */
  drainage_water_l_day: number;
  /** Daily total fertilizer mass dosed (grams), derived from irrigation volume and the EC target. */
  fertilizer_dosed_g_day: number;
  /** Daily-average fruit-set success rate (%) — the _fruit_set_temp_response factor. */
  fruit_set_pct: number;
  [key: string]: unknown;
}

export interface SimulationResult {
  greenhouse_name: string;
  summary: {
    final_yield_kg_m2: number;
    total_yield_kg: number;
    /** Hydroponics Level B: final_yield_kg_m2 after the EC-vs-reference dry-matter adjustment
     * (B1) -- higher EC concentrates fruit dry matter, so fresh-weight yield goes down. */
    ec_adjusted_final_yield_kg_m2: number;
    /** Hydroponics Level B2: fraction of ec_adjusted_final_yield_kg_m2 lost to BER
     * (Blossom End Rot) risk once EC exceeds the salinity threshold; 0 below it. */
    ber_yield_loss_fraction: number;
    /** Damped recipe tier (N/K/Mg/B): combined multiplicative yield effect, 1.0 when all four
     * are within their sufficiency range, floored so the tier can't swing yield too far. */
    recipe_adequacy_multiplier: number;
    /** Final marketable yield per m2 after B1, B2, and the damped recipe tier. */
    marketable_yield_kg_m2: number;
    total_marketable_yield_kg: number;
    area_m2: number;
    duration_days: number;
    total_heat_used_kwh: number;
    max_heat_available_kw: number;
    heat_loss_avoided_kwh: number;
    screen_deployed_pct: number;
    fan_pad_active_pct: number;
    total_dehumidification_elec_kwh: number;
    total_ventilation_elec_kwh: number;
    total_recirculation_elec_kwh: number;
    total_fertigation_elec_kwh: number;
    total_electricity_kwh: number;
    total_irrigation_water_m3: number;
    total_drainage_water_m3: number;
    total_fertilizer_dosed_kg: number;
    avg_fruit_set_pct: number;
    final_trusses_per_stem: number;
    avg_truss_rate_per_week: number;
    full_production_start_day: number;
    steady_state_truss_rate_per_week: number | null;
    co2_ambient_ppm: number;
    max_co2_available_ppm: number;
  };
  daily_series: DailyPoint[];
}

export interface WeatherPreviewPoint {
  date: string;
  temp_out_c: number;
  solar_rad_w_m2: number;
}

export interface WeatherPreview {
  daily_series: WeatherPreviewPoint[];
}

export interface SimulationOverrides {
  start_date?: string;
  duration_days?: number;
  crop_variety?: string;
  crop_density_plants_per_m2?: number;
  heating_setpoint_day_c?: number;
  heating_setpoint_night_c?: number;
  co2_setpoint_day_ppm?: number;
  dehumidification_setpoint_pct?: number;
  ec_target_ms_cm?: number;
  n_ppm?: number;
  k_ppm?: number;
  mg_ppm?: number;
  b_ppm?: number;
}

async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    throw new Error(`${path} failed: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export function getConfig(): Promise<GreenhouseConfig> {
  return getJson<GreenhouseConfig>("/config");
}

export function runSimulation(overrides: SimulationOverrides = {}): Promise<SimulationResult> {
  return getJson<SimulationResult>("/simulate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(overrides),
  });
}

export function getWeatherPreview(startDate?: string, durationDays?: number): Promise<WeatherPreview> {
  const params = new URLSearchParams();
  if (startDate) params.set("start_date", startDate);
  if (durationDays) params.set("duration_days", String(durationDays));
  const query = params.toString();
  return getJson<WeatherPreview>(`/weather_preview${query ? `?${query}` : ""}`);
}
