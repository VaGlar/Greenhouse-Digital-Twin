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
import { GreenhouseSchematic, type ZoneKey } from "./GreenhouseSchematic";
import {
  getConfig,
  runSimulation,
  type GreenhouseConfig,
  type SimulationOverrides,
  type SimulationResult,
} from "./api";

type TabKey = "crop" | "recipe" | "chp" | "weather" | "charts";

const TABS: { key: TabKey; label: string }[] = [
  { key: "crop", label: "🍅 Καλλιέργεια" },
  { key: "recipe", label: "🌡️ Συνταγή γεωπονίας" },
  { key: "chp", label: "🏗️ Θερμοκήπιο" },
  { key: "weather", label: "🌦️ Καιρός" },
  { key: "charts", label: "📈 Διαγράμματα" },
];

/** A tab click on a schematic zone (climate & humidity setpoints live in
 * "weather" — see GreenhouseSchematic's ZoneKey). */
const ZONE_TO_TAB: Record<ZoneKey, TabKey> = {
  climate: "weather",
  humidity: "weather",
  crop: "crop",
};

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

const CROP_SLIDERS: SliderDef[] = [
  {
    key: "crop_density_plants_per_m2",
    label: "Πυκνότητα φυτών",
    unit: " φ/m²",
    min: 2,
    max: 5,
    step: 0.25,
    optimal: [2.3, 3.0],
    note: "Εμπορικό στάνταρ single-stem high-wire: 2.3-2.5 φ/m² (Peet & Welles· VT Extension SPES-474).",
  },
];

/** Placeholder — real agronomy-recipe params (λίπανση/EC-pH, πρόγραμμα άρδευσης,
 * κλάδεμα/φορτίο ταξιανθιών, επικονίαση) δεν είναι ακόμα μοντελοποιημένα. */
const RECIPE_SLIDERS: SliderDef[] = [];

const WEATHER_SLIDERS: SliderDef[] = [
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
    optimal: [650, 750],
    note: "0ppm = καθόλου ανθρακολίπανση. Πάνω από ~700ppm το μοντέλο δεν δίνει επιπλέον yield.",
  },
  {
    key: "dehumidification_setpoint_pct",
    label: "Στόχος αφύγρανσης (RH)",
    unit: "%",
    min: 50,
    max: 90,
    step: 1,
    optimal: [65, 75],
    note: "65-75% είναι το βέλτιστο για επικονίαση. Πιο ξηρός αέρας ευνοεί το VPD photosynthesis optimum, trade-off με επικονίαση.",
  },
  { key: "duration_days", label: "Διάρκεια προσομοίωσης", unit: " μέρες", min: 30, max: 330, step: 10 },
];

const DEFAULT_SLIDER_VALUES: Record<SliderKey, number> = {
  crop_density_plants_per_m2: 3.5,
  heating_setpoint_day_c: 20,
  heating_setpoint_night_c: 17,
  co2_setpoint_day_ppm: 900,
  dehumidification_setpoint_pct: 70,
  duration_days: 330,
};

function App() {
  const [config, setConfig] = useState<GreenhouseConfig | null>(null);
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabKey>("chp");
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
    setActiveTab(ZONE_TO_TAB[zone]);
  }

  function setSlider(key: SliderKey, v: number) {
    setSliderValues((prev) => ({ ...prev, [key]: v }));
  }

  const latestDay = result?.daily_series.at(-1) ?? null;
  const showSchematic = activeTab !== "charts";

  return (
    <div className="dashboard">
      <header className="topbar">
        <div className="topbar-title">
          <h1>Greenhouse Digital Twin</h1>
          {config && <span className="topbar-badge">{config.crop.variety || "—"}</span>}
        </div>
        {config && (
          <p className="topbar-summary">
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

      <div className="dashboard-body">
        <aside className="sidebar">
          <nav className="sidebar-tabs">
            {TABS.map((t) => (
              <button
                key={t.key}
                className={`sidebar-tab ${activeTab === t.key ? "active" : ""}`}
                onClick={() => setActiveTab(t.key)}
              >
                {t.label}
              </button>
            ))}
          </nav>

          <div className="sidebar-content">
            {activeTab === "crop" && (
              <>
                {CROP_SLIDERS.map((s) => (
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
                    onChange={(v) => setSlider(s.key, v)}
                  />
                ))}
                <div className="side-field">
                  <label htmlFor="crop-variety">Ποικιλία</label>
                  <input
                    id="crop-variety"
                    type="text"
                    value={cropVariety}
                    onChange={(e) => setCropVariety(e.target.value)}
                  />
                </div>
              </>
            )}

            {activeTab === "recipe" && (
              <p className="side-note">
                Η συνταγή γεωπονίας (λίπανση/EC-pH, πρόγραμμα άρδευσης, κλάδεμα &amp; φορτίο
                ταξιανθιών, επικονίαση) δεν είναι ακόμα μοντελοποιημένη — θα προστεθεί εδώ όταν
                υλοποιηθεί. Οι στόχοι κλίματος (θερμοκρασία, CO₂, αφύγρανση) βρίσκονται πλέον στο
                tab «Καιρός».
              </p>
            )}

            {activeTab === "chp" && config && (
              <dl className="spec-list">
                <div className="spec-row">
                  <dt>Εμβαδόν</dt>
                  <dd>{config.geometry.area_m2.toLocaleString()} m²</dd>
                </div>
                <div className="spec-row">
                  <dt>Ύψος</dt>
                  <dd>{config.geometry.height_m.toFixed(2)} m</dd>
                </div>
                <div className="spec-row">
                  <dt>U-value κάλυψης</dt>
                  <dd>{config.geometry.cover_u_value_w_m2k.toFixed(1)} W/m²K</dd>
                </div>
                <div className="spec-row">
                  <dt>Διαπερατότητα</dt>
                  <dd>{(config.geometry.cover_transmissivity * 100).toFixed(0)}%</dd>
                </div>
                <div className="spec-row spec-row-section">
                  <dt>CHP ισχύς</dt>
                  <dd>{config.chp.electric_power_kw.toLocaleString()} kW</dd>
                </div>
                <div className="spec-row">
                  <dt>Λόγος θερμότητας/ισχύος</dt>
                  <dd>{config.chp.heat_to_power_ratio.toFixed(2)}</dd>
                </div>
                <div className="spec-row">
                  <dt>Θερμική ισχύς (σταθερή)</dt>
                  <dd>{(config.chp.electric_power_kw * config.chp.heat_to_power_ratio).toLocaleString()} kW</dd>
                </div>
                <div className="spec-row">
                  <dt>Fan-pad ψύξη</dt>
                  <dd>{config.climate_control.fan_pad_cooling_enabled ? "Ενεργή" : "Ανενεργή"}</dd>
                </div>
              </dl>
            )}

            {activeTab === "weather" && config && (
              <>
                <div className="side-field">
                  <label htmlFor="start-date">Ημερομηνία έναρξης</label>
                  <input
                    id="start-date"
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                  />
                </div>
                {WEATHER_SLIDERS.map((s) => (
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
                    onChange={(v) => setSlider(s.key, v)}
                  />
                ))}
                <p className="side-note">
                  ⓘ Θερμοκουρτίνα &amp; fan-pad: πλήρως αυτόματα (νύχτα/ζέστη/κρύο) — δες την
                  ένδειξη στο σχηματικό.
                </p>
                <dl className="spec-list">
                  <div className="spec-row">
                    <dt>Πηγή</dt>
                    <dd>{config.weather.source === "csv_typical_year" ? "Πραγματικά δεδομένα" : "Συνθετική"}</dd>
                  </div>
                  {config.weather.source === "csv_typical_year" && (
                    <div className="spec-row">
                      <dt>Περιοχή</dt>
                      <dd>Αλεξάνδρεια Ημαθίας</dd>
                    </div>
                  )}
                </dl>
              </>
            )}

            {activeTab === "charts" && (
              <p className="side-note">Τα αποτελέσματα εμφανίζονται δεξιά μετά την εκτέλεση.</p>
            )}
          </div>

          <div className="sidebar-footer">
            {error && <p className="error">{error}</p>}
            <button className="run-button" onClick={handleRun} disabled={loading}>
              {loading ? "Τρέχει…" : "Εκτέλεση προσομοίωσης"}
            </button>
          </div>
        </aside>

        <main className="main-area">
          {showSchematic && (
            <GreenhouseSchematic
              activeZone={null}
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
          )}

          {showSchematic && activeTab === "chp" && result && (
            <section className="stat-row">
              <StatTile label="Τελικό yield" value={`${result.summary.final_yield_kg_m2.toFixed(2)} kg/m²`} />
              <StatTile
                label="Συνολική παραγωγή"
                value={`${result.summary.total_yield_kg.toLocaleString(undefined, { maximumFractionDigits: 0 })} kg`}
              />
              <StatTile label="Διάρκεια" value={`${result.summary.duration_days} μέρες`} />
              <StatTile
                label="Θερμική κατανάλωση"
                value={`${result.summary.total_heat_used_kwh.toLocaleString(undefined, { maximumFractionDigits: 0 })} kWh`}
              />
              <StatTile
                label="Εξοικονόμηση από κουρτίνα"
                value={`${result.summary.heat_loss_avoided_kwh.toLocaleString(undefined, { maximumFractionDigits: 0 })} kWh`}
              />
            </section>
          )}

          {activeTab === "charts" && result && (
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
                <p className="chart-card-subtitle">
                  Μέγιστη ισχύς CHP: {result.summary.max_heat_available_kw.toLocaleString()} kW — η κατανάλωση δεν
                  μπορεί ποτέ να την ξεπεράσει.
                </p>
                <ResponsiveContainer width="100%" height={260}>
                  <LineChart data={result.daily_series} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                    <CartesianGrid stroke="var(--gridline)" vertical={false} />
                    <XAxis dataKey="date" stroke="var(--muted)" tick={{ fontSize: 12 }} minTickGap={40} />
                    <YAxis stroke="var(--muted)" tick={{ fontSize: 12 }} unit=" kW" width={56} />
                    <Tooltip contentStyle={{ background: "var(--surface-1)", border: "1px solid var(--gridline)" }} />
                    <Legend />
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
          )}

          {activeTab === "charts" && !result && (
            <p className="side-note">Τρέξε μια προσομοίωση για να δεις τα διαγράμματα.</p>
          )}
        </main>
      </div>
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
