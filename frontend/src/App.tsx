import { useEffect, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import "./App.css";
import { ParamSlider } from "./ParamSlider";
import {
  getConfig,
  runSimulation,
  type GreenhouseConfig,
  type SimulationOverrides,
  type SimulationResult,
} from "./api";

type SliderKey =
  | "crop_density_plants_per_m2"
  | "heating_setpoint_day_c"
  | "heating_setpoint_night_c"
  | "co2_setpoint_day_ppm"
  | "screen_energy_saving_fraction_pct"
  | "dehumidification_setpoint_pct"
  | "duration_days";

interface SliderDef {
  key: SliderKey;
  label: string;
  unit: string;
  min: number;
  max: number;
  step: number;
  optimal?: [number, number];
  note?: string;
}

interface SliderGroup {
  key: string;
  label: string;
  sliders: SliderDef[];
}

const SLIDER_GROUPS: SliderGroup[] = [
  {
    key: "crop",
    label: "🍅 Καλλιέργεια",
    sliders: [
      {
        key: "crop_density_plants_per_m2",
        label: "Πυκνότητα φυτών",
        unit: " φ/m²",
        min: 2,
        max: 5,
        step: 0.25,
        // Commercial single-stem high-wire greenhouse tomato: 2.3-2.5 plants/m2
        // is standard practice, pushed toward ~3 with a second stem per plant
        // (Peet & Welles, Greenhouse Tomato Production; VT Extension SPES-474).
        optimal: [2.3, 3.0],
      },
    ],
  },
  {
    key: "climate",
    label: "🌡️ Κλίμα",
    sliders: [
      {
        key: "heating_setpoint_day_c",
        label: "Θερμοκρασία ημέρας",
        unit: "°C",
        min: 16,
        max: 28,
        step: 0.5,
        optimal: [20, 24],
      },
      {
        key: "heating_setpoint_night_c",
        label: "Θερμοκρασία νύχτας",
        unit: "°C",
        min: 10,
        max: 22,
        step: 0.5,
        optimal: [14, 18],
      },
      {
        key: "co2_setpoint_day_ppm",
        label: "CO₂ ημέρας",
        unit: " ppm",
        min: 400,
        max: 1200,
        step: 25,
        optimal: [700, 1000],
      },
    ],
  },
  {
    key: "humidity",
    label: "💧 Υγρασία",
    sliders: [
      {
        key: "screen_energy_saving_fraction_pct",
        label: "Θερμοκουρτίνα (εξοικονόμηση, νύχτα)",
        unit: "%",
        min: 0,
        max: 80,
        step: 5,
      },
      {
        key: "dehumidification_setpoint_pct",
        label: "Στόχος αφύγρανσης (RH)",
        unit: "%",
        min: 50,
        max: 90,
        step: 1,
        // Literature range for greenhouse tomato RH is 60-85% (day 80-85%, night 65-75%);
        // 70% specifically cited as the pollination optimum — see docs/assumptions/climate-control.md
        optimal: [65, 75],
        note: "Το εύρος 65-75% είναι το βέλτιστο για επικονίαση. Για μέγιστο yield (βέλτιστο VPD ~0.85 kPa), το μοντέλο ευνοεί πιο ξηρό αέρα (~56-68% RH ανάλογα με τη θερμοκρασία) — trade-off μεταξύ επικονίασης και φωτοσύνθεσης.",
      },
    ],
  },
  {
    key: "run",
    label: "📅 Προσομοίωση",
    sliders: [
      { key: "duration_days", label: "Διάρκεια", unit: " μέρες", min: 30, max: 300, step: 10 },
    ],
  },
];

const DEFAULT_SLIDER_VALUES: Record<SliderKey, number> = {
  crop_density_plants_per_m2: 3.5,
  heating_setpoint_day_c: 20,
  heating_setpoint_night_c: 17,
  co2_setpoint_day_ppm: 900,
  screen_energy_saving_fraction_pct: 55,
  dehumidification_setpoint_pct: 70,
  duration_days: 150,
};

function App() {
  const [config, setConfig] = useState<GreenhouseConfig | null>(null);
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeGroup, setActiveGroup] = useState(SLIDER_GROUPS[0].key);
  const [sliderValues, setSliderValues] = useState<Record<SliderKey, number>>(DEFAULT_SLIDER_VALUES);
  const [cropVariety, setCropVariety] = useState("");
  const [startDate, setStartDate] = useState("");

  useEffect(() => {
    getConfig()
      .then((c) => {
        setConfig(c);
        setSliderValues({
          crop_density_plants_per_m2: c.crop.density_plants_per_m2,
          heating_setpoint_day_c: c.climate_control.heating_setpoint_day_c,
          heating_setpoint_night_c: c.climate_control.heating_setpoint_night_c,
          co2_setpoint_day_ppm: c.climate_control.co2_setpoint_day_ppm,
          screen_energy_saving_fraction_pct: Math.round(c.climate_control.screen_energy_saving_fraction * 100),
          dehumidification_setpoint_pct: c.climate_control.dehumidification_setpoint_pct,
          duration_days: c.simulation.duration_days,
        });
        setCropVariety(c.crop.variety);
        setStartDate(c.simulation.start_date);
      })
      .catch((e) => setError(String(e)));
  }, []);

  async function handleRun() {
    setLoading(true);
    setError(null);
    try {
      const { screen_energy_saving_fraction_pct, ...restSliderValues } = sliderValues;
      const overrides: SimulationOverrides = {
        ...restSliderValues,
        screen_energy_saving_fraction: screen_energy_saving_fraction_pct / 100,
        crop_variety: cropVariety || undefined,
        start_date: startDate || undefined,
      };
      setResult(await runSimulation(overrides));
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="viz-root">
      <header className="header">
        <h1>Greenhouse Digital Twin</h1>
        {config && (
          <p className="config-summary">
            {config.name} &middot; {config.geometry.area_m2.toLocaleString()} m&sup2; &middot;{" "}
            {config.chp.electric_power_kw.toLocaleString()} kW CHP &middot; {config.crop.variety}
          </p>
        )}
      </header>

      <section className="form-card">
        <h2>Παράμετροι προσομοίωσης</h2>
        <div className="form-groups">
          {SLIDER_GROUPS.map((g) => (
            <button
              key={g.key}
              className={`form-group-tab ${activeGroup === g.key ? "active" : ""}`}
              onClick={() => setActiveGroup(g.key)}
            >
              {g.label}
            </button>
          ))}
        </div>

        {SLIDER_GROUPS.map((g) =>
          activeGroup !== g.key ? null : (
            <div className="form-fields" key={g.key}>
              {g.sliders.map((s) => (
                <ParamSlider
                  key={s.key}
                  label={s.label}
                  unit={s.unit}
                  min={s.min}
                  max={s.max}
                  step={s.step}
                  optimal={s.optimal}
                  note={s.note}
                  value={sliderValues[s.key]}
                  onChange={(v) => setSliderValues((prev) => ({ ...prev, [s.key]: v }))}
                />
              ))}
              {g.key === "crop" && (
                <div className="form-field">
                  <label htmlFor="crop-variety">Ποικιλία</label>
                  <input
                    id="crop-variety"
                    type="text"
                    value={cropVariety}
                    onChange={(e) => setCropVariety(e.target.value)}
                  />
                </div>
              )}
              {g.key === "run" && (
                <div className="form-field">
                  <label htmlFor="start-date">Ημερομηνία έναρξης</label>
                  <input
                    id="start-date"
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                  />
                </div>
              )}
            </div>
          )
        )}
      </section>

      <button className="run-button" onClick={handleRun} disabled={loading}>
        {loading ? "Τρέχει η προσομοίωση…" : "Run simulation"}
      </button>

      {error && <p className="error">{error}</p>}

      {result && (
        <>
          <section className="stat-row">
            <StatTile label="Τελικό yield" value={`${result.summary.final_yield_kg_m2.toFixed(2)} kg/m²`} />
            <StatTile label="Συνολική παραγωγή" value={`${result.summary.total_yield_kg.toLocaleString(undefined, { maximumFractionDigits: 0 })} kg`} />
            <StatTile label="Διάρκεια" value={`${result.summary.duration_days} μέρες`} />
          </section>

          <section className="chart-card">
            <h2>Θερμοκρασία</h2>
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={result.daily_series} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="var(--gridline)" vertical={false} />
                <XAxis dataKey="date" stroke="var(--muted)" tick={{ fontSize: 12 }} minTickGap={40} />
                <YAxis stroke="var(--muted)" tick={{ fontSize: 12 }} unit="°C" width={48} />
                <Tooltip contentStyle={{ background: "var(--surface-1)", border: "1px solid var(--gridline)" }} />
                <Legend />
                <Line type="monotone" dataKey="temp_in_c" name="Εσωτερική" stroke="var(--series-1)" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="temp_out_c" name="Εξωτερική" stroke="var(--series-2)" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </section>

          <section className="chart-card">
            <h2>CO2 εσωτερικού χώρου</h2>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={result.daily_series} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="var(--gridline)" vertical={false} />
                <XAxis dataKey="date" stroke="var(--muted)" tick={{ fontSize: 12 }} minTickGap={40} />
                <YAxis stroke="var(--muted)" tick={{ fontSize: 12 }} unit=" ppm" width={56} />
                <Tooltip contentStyle={{ background: "var(--surface-1)", border: "1px solid var(--gridline)" }} />
                <Line type="monotone" dataKey="co2_in_ppm" name="CO2" stroke="var(--series-3)" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </section>

          <section className="chart-card">
            <h2>Σχετική υγρασία εσωτερικού χώρου</h2>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={result.daily_series} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="var(--gridline)" vertical={false} />
                <XAxis dataKey="date" stroke="var(--muted)" tick={{ fontSize: 12 }} minTickGap={40} />
                <YAxis stroke="var(--muted)" tick={{ fontSize: 12 }} unit="%" width={48} domain={[0, 100]} />
                <Tooltip contentStyle={{ background: "var(--surface-1)", border: "1px solid var(--gridline)" }} />
                <Line type="monotone" dataKey="rh_in_pct" name="RH" stroke="var(--series-1)" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </section>

          <section className="chart-card">
            <h2>VPD (έλλειμμα πίεσης υδρατμών)</h2>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={result.daily_series} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="var(--gridline)" vertical={false} />
                <XAxis dataKey="date" stroke="var(--muted)" tick={{ fontSize: 12 }} minTickGap={40} />
                <YAxis stroke="var(--muted)" tick={{ fontSize: 12 }} unit=" kPa" width={56} />
                <Tooltip contentStyle={{ background: "var(--surface-1)", border: "1px solid var(--gridline)" }} />
                <Line type="monotone" dataKey="vpd_kpa" name="VPD" stroke="var(--series-2)" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </section>

          <section className="chart-card">
            <h2>Σωρευτική παραγωγή τομάτας</h2>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={result.daily_series} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="var(--gridline)" vertical={false} />
                <XAxis dataKey="date" stroke="var(--muted)" tick={{ fontSize: 12 }} minTickGap={40} />
                <YAxis stroke="var(--muted)" tick={{ fontSize: 12 }} unit=" kg/m²" width={64} />
                <Tooltip contentStyle={{ background: "var(--surface-1)", border: "1px solid var(--gridline)" }} />
                <Line type="monotone" dataKey="fruit_fresh_yield_kg_m2" name="Yield" stroke="var(--series-4)" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </section>
        </>
      )}
    </div>
  );
}

function StatTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="stat-tile">
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}</span>
    </div>
  );
}

export default App;
