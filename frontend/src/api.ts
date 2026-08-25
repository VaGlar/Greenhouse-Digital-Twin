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
  geometry: { area_m2: number; height_m: number };
  chp: { electric_power_kw: number; heat_to_power_ratio: number; co2_kg_per_kwh_elec: number };
  crop: { variety: string; planting_date: string; density_plants_per_m2: number };
  simulation: { start_date: string; duration_days: number; timestep_hours: number };
  climate_control: {
    heating_setpoint_day_c: number;
    heating_setpoint_night_c: number;
    co2_setpoint_day_ppm: number;
    screen_energy_saving_fraction: number;
    dehumidification_setpoint_pct: number;
    [key: string]: unknown;
  };
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
}

export interface SimulationResult {
  greenhouse_name: string;
  summary: {
    final_yield_kg_m2: number;
    total_yield_kg: number;
    area_m2: number;
    duration_days: number;
    total_heat_used_kwh: number;
    max_heat_available_kw: number;
    heat_loss_avoided_kwh: number;
    screen_deployed_pct: number;
    co2_ambient_ppm: number;
    max_co2_available_ppm: number;
  };
  daily_series: DailyPoint[];
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
