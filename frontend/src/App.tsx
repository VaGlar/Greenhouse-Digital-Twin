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
import { getConfig, runSimulation, type GreenhouseConfig, type SimulationResult } from "./api";

function App() {
  const [config, setConfig] = useState<GreenhouseConfig | null>(null);
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getConfig()
      .then(setConfig)
      .catch((e) => setError(String(e)));
  }, []);

  async function handleRun() {
    setLoading(true);
    setError(null);
    try {
      setResult(await runSimulation());
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
