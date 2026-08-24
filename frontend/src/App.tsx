import { useEffect, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import "./App.css";
import { ParamSlider } from "./ParamSlider";
import { GreenhouseSchematic, type ZoneKey } from "./GreenhouseSchematic";
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
  /** Matching GreenhouseSchematic zone — clicking that zone scrolls here. */
  zone: ZoneKey | null;
  sliders: SliderDef[];
}

const SLIDER_GROUPS: SliderGroup[] = [
  {
    key: "climate",
    label: "🌡️ Κλίμα",
    zone: "climate",
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
        min: 0,
        max: 1000,
        step: 25,
        // Study testing 500/700/850/1000 ppm on tomato found 700ppm optimal, no
        // yield benefit above it — see papers/tomato-co2-optimum-700ppm.md.
        // Min=0 covers greenhouses that don't dose CO2 at all (ambient ~420ppm only).
        optimal: [650, 750],
        note: "0ppm = καθόλου ανθρακολίπανση (μόνο ambient CO2). Πάνω από ~700ppm το μοντέλο δεν δίνει επιπλέον yield.",
      },
    ],
  },
  {
    key: "humidity",
    label: "💧 Υγρασία",
    zone: "humidity",
    sliders: [
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
    key: "crop",
    label: "🍅 Καλλιέργεια",
    zone: "crop",
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
    key: "run",
    label: "📅 Προσομοίωση",
    zone: null,
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
  dehumidification_setpoint_pct: 70,
  duration_days: 150,
};

function App() {
  const [config, setConfig] = useState<GreenhouseConfig | null>(null);
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeZone, setActiveZone] = useState<ZoneKey | null>(null);
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
      const overrides: SimulationOverrides = {
        ...sliderValues,
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

  function handleZoneClick(zone: ZoneKey) {
    setActiveZone(zone);
    const group = SLIDER_GROUPS.find((g) => g.zone === zone);
    if (group) {
      document.getElementById(`zone-${group.key}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  const latestDay = result?.daily_series.at(-1) ?? null;

  return (
    <div className="viz-root">
      <header className="header">
        <div className="header-title-row">
          <h1>Greenhouse Digital Twin</h1>
          {config && (
            <span className="header-badge">{config.crop.variety || "—"}</span>
          )}
        </div>
        {config && (
          <p className="config-summary">
            {config.name} &middot; {config.geometry.area_m2.toLocaleString()} m&sup2; &middot;{" "}
            {config.chp.electric_power_kw.toLocaleString()} kW CHP
            {result && (
              <>
                {" "}&middot; ημέρα {result.summary.duration_days} &middot; yield{" "}
                {result.summary.final_yield_kg_m2.toFixed(2)} kg/m²
              </>
            )}
          </p>
        )}
      </header>

      <GreenhouseSchematic
        activeZone={activeZone}
        onZoneClick={handleZoneClick}
        outdoorTempC={latestDay?.temp_out_c ?? null}
        indoorTempC={latestDay?.temp_in_c ?? null}
        rhPct={latestDay?.rh_in_pct ?? null}
        vpdKpa={latestDay?.vpd_kpa ?? null}
        co2Ppm={latestDay?.co2_in_ppm ?? null}
        screenSavingPct={config ? config.climate_control.screen_energy_saving_fraction * 100 : 55}
        screenDeployedPct={result?.summary.screen_deployed_pct ?? null}
        dehumidSetpointPct={sliderValues.dehumidification_setpoint_pct}
        yieldKgM2={latestDay?.fruit_fresh_yield_kg_m2 ?? null}
      />

      <section className="form-card">
        <h2>Παράμετροι προσομοίωσης</h2>

        {SLIDER_GROUPS.map((g) => (
          <div className="form-fields" id={`zone-${g.key}`} key={g.key}>
            <h3 className="form-group-heading">{g.label}</h3>
            <div className="form-fields-grid">
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
              {g.key === "humidity" && (
                <p className="form-group-info">
                  ⓘ Η θερμοκουρτίνα λειτουργεί πλήρως αυτόματα — κλείνει τη νύχτα, όταν κάνει
                  πολλή ζέστη (σκίαση, ακόμα κι αν ο αερισμός φτάσει στο μέγιστό του), ή όταν
                  κάνει κρύο και η CHP δεν επαρκεί, εφόσον η μόνωση συμφέρει περισσότερο από τον
                  χαμένο ήλιο. Δεν ρυθμίζεται χειροκίνητα — δες την ένδειξη στο διάγραμμα
                  παραπάνω και τα γραφήματα κατανάλωσης/ωρών κλειστής κάτω.
                </p>
              )}
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
          </div>
        ))}
      </section>

      <button className="run-button" onClick={handleRun} disabled={loading}>
        {loading ? "Τρέχει η προσομοίωση…" : "Εκτέλεση προσομοίωσης"}
      </button>

      {error && <p className="error">{error}</p>}

      {result && (
        <>
          <section className="stat-row">
            <StatTile label="Τελικό yield" value={`${result.summary.final_yield_kg_m2.toFixed(2)} kg/m²`} />
            <StatTile label="Συνολική παραγωγή" value={`${result.summary.total_yield_kg.toLocaleString(undefined, { maximumFractionDigits: 0 })} kg`} />
            <StatTile label="Διάρκεια" value={`${result.summary.duration_days} μέρες`} />
            <StatTile label="Θερμική κατανάλωση" value={`${result.summary.total_heat_used_kwh.toLocaleString(undefined, { maximumFractionDigits: 0 })} kWh`} />
            <StatTile label="Εξοικονόμηση από κουρτίνα" value={`${result.summary.heat_loss_avoided_kwh.toLocaleString(undefined, { maximumFractionDigits: 0 })} kWh`} />
          </section>

          <div className="chart-grid">
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
            <h2>Θερμική κατανάλωση (μέση ισχύς/ώρα)</h2>
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={result.daily_series} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="var(--gridline)" vertical={false} />
                <XAxis dataKey="date" stroke="var(--muted)" tick={{ fontSize: 12 }} minTickGap={40} />
                <YAxis stroke="var(--muted)" tick={{ fontSize: 12 }} unit=" kW" width={56} />
                <Tooltip contentStyle={{ background: "var(--surface-1)", border: "1px solid var(--gridline)" }} />
                <Legend />
                <ReferenceLine
                  y={result.summary.max_heat_available_kw}
                  stroke="var(--amber)"
                  strokeDasharray="5 4"
                  label={{ value: "Μέγιστη ισχύς CHP", position: "insideTopRight", fill: "var(--amber)", fontSize: 11 }}
                />
                <Line type="monotone" dataKey="heat_used_kw" name="Μέση ισχύς" stroke="var(--energy)" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </section>

          <section className="chart-card">
            <h2>Ώρες κλειστής θερμοκουρτίνας/ημέρα</h2>
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={result.daily_series} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="var(--gridline)" vertical={false} />
                <XAxis dataKey="date" stroke="var(--muted)" tick={{ fontSize: 12 }} minTickGap={40} />
                <YAxis stroke="var(--muted)" tick={{ fontSize: 12 }} unit="h" width={40} domain={[0, 24]} />
                <Tooltip contentStyle={{ background: "var(--surface-1)", border: "1px solid var(--gridline)" }} />
                <Line type="monotone" dataKey="screen_closed_hours" name="Κλειστή" stroke="var(--humidity)" strokeWidth={2} dot={false} />
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
                <Line type="monotone" dataKey="rh_in_pct" name="RH" stroke="var(--humidity)" strokeWidth={2} dot={false} />
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
                <Line type="monotone" dataKey="vpd_kpa" name="VPD" stroke="var(--humidity)" strokeWidth={2} dot={false} />
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
          </div>
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
