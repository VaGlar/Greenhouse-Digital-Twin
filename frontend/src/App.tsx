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
  getWeatherPreview,
  runSimulation,
  type DailyPoint,
  type GreenhouseConfig,
  type SimulationOverrides,
  type SimulationResult,
  type WeatherPreview,
} from "./api";

type TabKey = "crop" | "recipe" | "chp" | "weather" | "charts";

const TABS: { key: TabKey; label: string }[] = [
  { key: "chp", label: "🏗️ Θερμοκήπιο" },
  { key: "crop", label: "🍅 Καλλιέργεια" },
  { key: "recipe", label: "🌡️ Συνταγή γεωπονίας" },
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
  const [weatherPreview, setWeatherPreview] = useState<WeatherPreview | null>(null);
  const [baselineResult, setBaselineResult] = useState<SimulationResult | null>(null);
  // null = "live" (always the run's last simulated day) -- an explicit index means the user has
  // scrubbed back to inspect an earlier day, mirroring how this twin will eventually be paused at
  // "today" while the real greenhouse is mid-cycle, rather than always jumped to the season's end.
  const [viewedDayIndex, setViewedDayIndex] = useState<number | null>(null);

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

  useEffect(() => {
    if (activeTab !== "weather" || !startDate) return;
    getWeatherPreview(startDate, sliderValues.duration_days)
      .then(setWeatherPreview)
      .catch(() => setWeatherPreview(null));
  }, [activeTab, startDate, sliderValues.duration_days]);

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
      setViewedDayIndex(null); // new run -- snap the scrubber back to "live" (its last day)
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

  const viewedDayIdx = result ? (viewedDayIndex ?? result.daily_series.length - 1) : 0;
  const viewedDay = result?.daily_series[viewedDayIdx] ?? null;
  const showSchematic = activeTab === "chp";
  const meanIndoorTempC = result
    ? result.daily_series.reduce((sum, d) => sum + d.temp_in_c, 0) / result.daily_series.length
    : null;
  const isCompare = Boolean(result && baselineResult);
  const chartData = result ? (baselineResult ? mergeForCompare(result.daily_series, baselineResult.daily_series) : result.daily_series) : [];
  const xKey = isCompare ? "day" : "date";
  // Where the scrubber's selected day lands on the x-axis -- a plain day index in compare mode,
  // the matching calendar date otherwise. Only draws a marker when scrubbed back from "live".
  const viewedX = result && viewedDayIndex !== null ? (isCompare ? viewedDayIndex : result.daily_series[viewedDayIndex]?.date) : undefined;

  // Shared chart definitions -- reused across the crop/weather tabs (a relevant subset,
  // so parameter changes are visible without switching tabs) and the charts tab (full set).
  const tempChart = (
    <ComparableChart
      title="Θερμοκρασία"
      unit="°C"
      height={260}
      data={chartData}
      xKey={xKey}
      viewedX={viewedX}
      series={buildSeries(
        [
          { key: "temp_in_c", name: "Εσωτερική", color: "var(--series-1)" },
          { key: "temp_out_c", name: "Εξωτερική", color: "var(--series-2)" },
        ],
        isCompare,
      )}
    />
  );
  const heatChart = result && (
    <ComparableChart
      title="Θερμική κατανάλωση (μέση ισχύς/ώρα)"
      subtitle={`Μέγιστη ισχύς CHP: ${result.summary.max_heat_available_kw.toLocaleString()} kW — η κατανάλωση δεν μπορεί ποτέ να την ξεπεράσει.`}
      unit=" kW"
      height={260}
      data={chartData}
      xKey={xKey}
      viewedX={viewedX}
      series={buildSeries([{ key: "heat_used_kw", name: "Μέση ισχύς", color: "var(--energy)" }], isCompare)}
    />
  );
  const screenChart = (
    <ComparableChart
      title="Ώρες κλειστής θερμοκουρτίνας/ημέρα"
      unit="h"
      height={260}
      domain={[0, 24]}
      data={chartData}
      xKey={xKey}
      viewedX={viewedX}
      series={buildSeries([{ key: "screen_closed_hours", name: "Κλειστή", color: "var(--humidity)" }], isCompare)}
    />
  );
  const electricityChart = (
    <ComparableChart
      title="Ηλεκτρική κατανάλωση θερμοκηπίου (μέση ισχύς/ώρα)"
      unit=" kW"
      height={260}
      data={chartData}
      xKey={xKey}
      viewedX={viewedX}
      series={buildSeries(
        [
          { key: "dehumidification_elec_kw", name: "Αφύγρανση", color: "var(--energy)" },
          { key: "ventilation_elec_kw", name: "Αερισμός/fan-pad", color: "var(--series-2)" },
          { key: "recirculation_elec_kw", name: "Ανακυκλοφορία", color: "var(--series-1)" },
          { key: "fertigation_elec_kw", name: "Λίπανση/άρδευση", color: "var(--humidity)" },
        ],
        isCompare,
      )}
    />
  );
  const fanPadChart = (
    <ComparableChart
      title="Ώρες ενεργού fan-pad ψύξης/ημέρα"
      unit="h"
      height={260}
      domain={[0, 24]}
      data={chartData}
      xKey={xKey}
      viewedX={viewedX}
      series={buildSeries([{ key: "fan_pad_active_hours", name: "Ενεργό", color: "var(--series-1)" }], isCompare)}
    />
  );
  const rhChart = (
    <ComparableChart
      title="Σχετική υγρασία εσωτερικού χώρου"
      unit="%"
      height={220}
      domain={[0, 100]}
      data={chartData}
      xKey={xKey}
      viewedX={viewedX}
      series={buildSeries([{ key: "rh_in_pct", name: "RH", color: "var(--humidity)" }], isCompare)}
    />
  );
  const vpdChart = (
    <ComparableChart
      title="VPD (έλλειμμα πίεσης υδρατμών)"
      unit=" kPa"
      height={220}
      data={chartData}
      xKey={xKey}
      viewedX={viewedX}
      series={buildSeries([{ key: "vpd_kpa", name: "VPD", color: "var(--humidity)" }], isCompare)}
    />
  );
  const yieldChart = (
    <ComparableChart
      title="Σωρευτική παραγωγή τομάτας"
      unit=" kg/m²"
      height={320}
      data={chartData}
      xKey={xKey}
      viewedX={viewedX}
      series={buildSeries([{ key: "fruit_fresh_yield_kg_m2", name: "Yield", color: "var(--series-4)" }], isCompare)}
    />
  );
  const fruitSetChart = (
    <ComparableChart
      title="Fruit Set % (επιτυχία γονιμοποίησης)"
      unit="%"
      height={220}
      domain={[0, 100]}
      data={chartData}
      xKey={xKey}
      viewedX={viewedX}
      series={buildSeries([{ key: "fruit_set_pct", name: "Fruit Set", color: "var(--series-3)" }], isCompare)}
    />
  );
  const irrigationChart = (
    <ComparableChart
      title="Άρδευση / στράγγιση (L/ημέρα)"
      subtitle="Η άρδευση ακολουθεί τη διαπνοή του φυτού συν το στόχο drainage — δες tab «Καλλιέργεια»."
      unit=" L"
      height={220}
      data={chartData}
      xKey={xKey}
      viewedX={viewedX}
      series={buildSeries(
        [
          { key: "irrigation_water_l_day", name: "Άρδευση", color: "var(--humidity)" },
          { key: "drainage_water_l_day", name: "Στράγγιση", color: "var(--series-2)" },
        ],
        isCompare,
      )}
    />
  );

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
                {config && (
                  <dl className="spec-list">
                    <div className="spec-row">
                      <dt>Target βάρος καρπού</dt>
                      <dd>{config.crop.target_fruit_weight_g.toFixed(0)} g</dd>
                    </div>
                    <div className="spec-row">
                      <dt>Καρποί/τσαμπί</dt>
                      <dd>{config.crop.fruits_per_truss.toFixed(0)}</dd>
                    </div>
                    <div className="spec-row">
                      <dt>Στελέχη/φυτό</dt>
                      <dd>{config.crop.stems_per_plant.toFixed(0)}</dd>
                    </div>
                    <div className="spec-row spec-row-section">
                      <dt>Σύστημα υδροπονίας</dt>
                      <dd>{config.hydroponic.substrate_type}</dd>
                    </div>
                    <div className="spec-row">
                      <dt>EC θρεπτικού διαλύματος</dt>
                      <dd>{config.hydroponic.ec_target_ms_cm.toFixed(1)} mS/cm</dd>
                    </div>
                    <div className="spec-row">
                      <dt>pH θρεπτικού διαλύματος</dt>
                      <dd>{config.hydroponic.ph_target.toFixed(1)}</dd>
                    </div>
                    <div className="spec-row">
                      <dt>Στόχος drainage</dt>
                      <dd>{(config.hydroponic.drainage_target_fraction * 100).toFixed(0)}%</dd>
                    </div>
                  </dl>
                )}
                {config && (
                  <CropPhaseTimeline
                    durationDays={sliderValues.duration_days}
                    fruitingStartDays={config.crop.fruiting_start_days}
                    fruitingRampDays={config.crop.fruiting_ramp_days}
                  />
                )}
                {result && (
                  <div className="side-field">
                    <span className="side-field-label">Σωρευτική παραγωγή μέχρι τώρα</span>
                    <Sparkline data={result.daily_series} dataKey="fruit_fresh_yield_kg_m2" color="var(--series-4)" />
                  </div>
                )}
              </>
            )}

            {activeTab === "recipe" && (
              <>
                <p className="side-note">
                  Η λίπανση/άρδευση (EC/pH/drainage) μετακόμισε στο tab «Καλλιέργεια» — πλέον
                  τροφοδοτεί πραγματικά την προσομοίωση (νερό, ηλεκτρικό αντλίας, λίπασμα). Το
                  φορτίο καρπού/κλάδεμα (στελέχη/φυτό, καρποί/τσαμπί) βρίσκεται επίσης εκεί. Η
                  επικονίαση παρακάτω παραμένει <strong>πληροφοριακή</strong> —{" "}
                  <strong>δεν επηρεάζει ακόμα την προσομοίωση</strong>. Οι στόχοι κλίματος
                  (θερμοκρασία, CO₂, αφύγρανση) βρίσκονται στο tab «Καιρός».
                </p>
                <dl className="spec-list">
                  <div className="spec-section-label">Επικονίαση</div>
                  <div className="spec-row">
                    <dt>Μέθοδος</dt>
                    <dd>Κυψέλες Bombus terrestris</dd>
                  </div>
                  <div className="spec-row">
                    <dt>Πυκνότητα κυψελών</dt>
                    <dd>~1 / 500–1.000 m²</dd>
                  </div>
                </dl>
              </>
            )}

            {activeTab === "chp" && config && (
              <>
                {result && viewedDay && (
                  <>
                    <PowerGauge
                      label="Θερμική ισχύς (προβαλλόμενη ημέρα)"
                      value={viewedDay.heat_used_kw}
                      max={result.summary.max_heat_available_kw}
                      unit=" kW"
                    />
                    <ScreenStatusBadge hours={viewedDay.screen_closed_hours} />
                    <FanPadStatusBadge hours={viewedDay.fan_pad_active_hours} />
                  </>
                )}
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
                  <div className="spec-row">
                    <dt>Ανεμιστήρες ανακυκλοφορίας</dt>
                    <dd>~35 × ACF21 ({config.climate_control.recirculation_fan_power_kw} kW)</dd>
                  </div>
                </dl>
              </>
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
                  ένδειξή τους στο tab «Θερμοκήπιο».
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
                {weatherPreview && (
                  <div className="side-field">
                    <span className="side-field-label">
                      Προεπισκόπηση καιρού (πριν την προσομοίωση): εξωτ. θερμοκρασία &amp; ακτινοβολία
                    </span>
                    <ResponsiveContainer width="100%" height={110}>
                      <LineChart
                        data={weatherPreview.daily_series}
                        margin={{ top: 4, right: 4, left: 4, bottom: 0 }}
                      >
                        <XAxis dataKey="date" hide />
                        <YAxis yAxisId="temp" hide domain={["auto", "auto"]} />
                        <YAxis yAxisId="solar" hide orientation="right" domain={[0, "auto"]} />
                        <Tooltip
                          contentStyle={{ background: "var(--surface-1)", border: "1px solid var(--gridline)" }}
                        />
                        <Line
                          yAxisId="temp"
                          type="monotone"
                          dataKey="temp_out_c"
                          name="Εξωτ. θερμοκρασία (°C)"
                          stroke="var(--series-2)"
                          strokeWidth={1.5}
                          dot={false}
                          isAnimationActive={false}
                        />
                        <Line
                          yAxisId="solar"
                          type="monotone"
                          dataKey="solar_rad_w_m2"
                          name="Ακτινοβολία (W/m²)"
                          stroke="var(--amber)"
                          strokeWidth={1.5}
                          dot={false}
                          isAnimationActive={false}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </>
            )}

            {activeTab === "charts" && (
              <>
                <p className="side-note">Τα αποτελέσματα εμφανίζονται δεξιά μετά την εκτέλεση.</p>
                {result && (
                  <>
                    {!baselineResult ? (
                      <button className="secondary-button" onClick={() => setBaselineResult(result)}>
                        📌 Καρφίτσωμα ως baseline
                      </button>
                    ) : (
                      <button className="secondary-button" onClick={() => setBaselineResult(null)}>
                        ✕ Αφαίρεση baseline
                      </button>
                    )}
                    <p className="side-note">
                      {baselineResult
                        ? "Τα διαγράμματα δείχνουν το τρέχον τρέξιμο (συνεχής γραμμή) πάνω στο καρφιτσωμένο baseline (διακεκομμένη), κατά ημέρα προσομοίωσης."
                        : "Καρφίτσωσε το τρέχον αποτέλεσμα, άλλαξε παραμέτρους, τρέξε ξανά και σύγκρινε τα δύο σενάρια σε επικάλυψη."}
                    </p>
                    <button className="secondary-button" onClick={() => downloadCsv(result)}>
                      ⬇ Εξαγωγή CSV
                    </button>
                  </>
                )}
              </>
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
          {result && (
            <DayScrubber
              daily={result.daily_series}
              viewedIndex={viewedDayIdx}
              isLive={viewedDayIndex === null}
              onChange={setViewedDayIndex}
            />
          )}

          {showSchematic && (
            <GreenhouseSchematic
              activeZone={null}
              onZoneClick={handleZoneClick}
              outdoorTempC={viewedDay?.temp_out_c ?? null}
              indoorTempC={viewedDay?.temp_in_c ?? null}
              rhPct={viewedDay?.rh_in_pct ?? null}
              vpdKpa={viewedDay?.vpd_kpa ?? null}
              co2Ppm={viewedDay?.co2_in_ppm ?? null}
              screenSavingPct={config ? config.climate_control.screen_energy_saving_fraction * 100 : 55}
              screenDeployedPct={result?.summary.screen_deployed_pct ?? null}
              dehumidSetpointPct={sliderValues.dehumidification_setpoint_pct}
              yieldKgM2={viewedDay?.fruit_fresh_yield_kg_m2 ?? null}
            />
          )}

          {result && <div className="chart-grid pinned-yield">{yieldChart}</div>}

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
              <StatTile
                label="Ηλεκτρική κατανάλωση (δίκτυο)"
                value={`${result.summary.total_electricity_kwh.toLocaleString(undefined, { maximumFractionDigits: 0 })} kWh`}
              />
            </section>
          )}

          {activeTab === "recipe" && (
            <p className="side-note">
              Η συνταγή γεωπονίας δεν επηρεάζει ακόμα την προσομοίωση, οπότε δεν υπάρχουν
              αποτελέσματα να δείξουμε εδώ.
            </p>
          )}

          {activeTab === "crop" && (
            <>
              {result ? (
                <>
                  <section className="stat-row">
                    <StatTile label="Τελικό yield" value={`${result.summary.final_yield_kg_m2.toFixed(2)} kg/m²`} />
                    <StatTile
                      label="Συνολική παραγωγή"
                      value={`${result.summary.total_yield_kg.toLocaleString(undefined, { maximumFractionDigits: 0 })} kg`}
                    />
                    <StatTile label="Μέσο Fruit Set" value={`${result.summary.avg_fruit_set_pct.toFixed(0)}%`} />
                    <StatTile
                      label="Ρυθμός ταξιανθιών/στέλεχος (όλη η περίοδος)"
                      value={`${result.summary.avg_truss_rate_per_week.toFixed(2)}/εβδ`}
                    />
                    <StatTile
                      label="Ρυθμός ταξιανθιών/στέλεχος (σταθερή φάση)"
                      value={
                        result.summary.steady_state_truss_rate_per_week === null
                          ? "—"
                          : `${result.summary.steady_state_truss_rate_per_week.toFixed(2)}/εβδ`
                      }
                    />
                  </section>
                  <section className="stat-row">
                    <StatTile
                      label="Συνολική άρδευση"
                      value={`${result.summary.total_irrigation_water_m3.toLocaleString(undefined, { maximumFractionDigits: 0 })} m³`}
                    />
                    <StatTile
                      label="Συνολική στράγγιση"
                      value={`${result.summary.total_drainage_water_m3.toLocaleString(undefined, { maximumFractionDigits: 0 })} m³`}
                    />
                    <StatTile
                      label="Λίπασμα δοσομετρημένο"
                      value={`${result.summary.total_fertilizer_dosed_kg.toLocaleString(undefined, { maximumFractionDigits: 0 })} kg`}
                    />
                    <StatTile
                      label="Ηλεκτρικό λίπανσης/άρδευσης"
                      value={`${result.summary.total_fertigation_elec_kwh.toLocaleString(undefined, { maximumFractionDigits: 0 })} kWh`}
                    />
                  </section>
                  <div className="chart-grid">
                    {fruitSetChart}
                    {irrigationChart}
                  </div>
                </>
              ) : (
                <p className="side-note">Τρέξε μια προσομοίωση για να δεις αποτελέσματα καλλιέργειας.</p>
              )}
              {result && (
                <button className="secondary-button jump-to-charts" onClick={() => setActiveTab("charts")}>
                  📈 Δες όλα τα διαγράμματα
                </button>
              )}
            </>
          )}

          {activeTab === "weather" && (
            <>
              {result && meanIndoorTempC !== null ? (
                <>
                  <section className="stat-row">
                    <StatTile label="Μέση εσωτερική θερμοκρασία" value={`${meanIndoorTempC.toFixed(1)}°C`} />
                    <StatTile
                      label="Θερμική κατανάλωση"
                      value={`${result.summary.total_heat_used_kwh.toLocaleString(undefined, { maximumFractionDigits: 0 })} kWh`}
                    />
                    <StatTile label="Κουρτίνα κλειστή" value={`${result.summary.screen_deployed_pct.toFixed(0)}%`} />
                  </section>
                  <div className="chart-grid">
                    {tempChart}
                    {heatChart}
                    {electricityChart}
                    {screenChart}
                    {fanPadChart}
                    {rhChart}
                    {vpdChart}
                  </div>
                </>
              ) : (
                <p className="side-note">Τρέξε μια προσομοίωση για να δεις τα αποτελέσματα κλίματος.</p>
              )}
              {result && (
                <button className="secondary-button jump-to-charts" onClick={() => setActiveTab("charts")}>
                  📈 Δες όλα τα διαγράμματα
                </button>
              )}
            </>
          )}

          {activeTab === "charts" && result && (
            <div className="chart-grid">
              {tempChart}
              {heatChart}
              {electricityChart}
              {screenChart}
              {fanPadChart}
              {rhChart}
              {vpdChart}
              {fruitSetChart}
              {irrigationChart}
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

/** Lets the user "step forward" through an already-completed run's simulated days --
 * useful now for inspecting an earlier point in the season (the schematic, gauges,
 * and every ComparableChart's reference-line marker all follow the viewed day), and
 * the same slider will later double as how this twin gets paused at "today" once it
 * runs alongside a real, still-in-progress greenhouse rather than a finished batch run. */
function DayScrubber({
  daily,
  viewedIndex,
  isLive,
  onChange,
}: {
  daily: DailyPoint[];
  viewedIndex: number;
  isLive: boolean;
  onChange: (index: number | null) => void;
}) {
  const maxIdx = daily.length - 1;
  const viewedDate = daily[viewedIndex]?.date;
  const presetDays = [10, 20, 50, 100, 200].filter((d) => d <= maxIdx + 1);

  return (
    <section className="day-scrubber">
      <div className="day-scrubber-head">
        <span className="day-scrubber-label">
          Ημέρα {viewedIndex + 1} / {maxIdx + 1}
          {viewedDate ? ` · ${viewedDate}` : ""}
          {isLive && <span className="day-scrubber-live"> · τρέχουσα</span>}
        </span>
        {!isLive && (
          <button className="secondary-button" onClick={() => onChange(null)}>
            ⏭ Μετάβαση στο τέλος
          </button>
        )}
      </div>
      <input
        type="range"
        className="day-scrubber-range"
        min={0}
        max={maxIdx}
        value={viewedIndex}
        onChange={(e) => onChange(Number(e.target.value))}
      />
      <div className="day-scrubber-presets">
        {presetDays.map((d) => (
          <button key={d} className="day-scrubber-chip" onClick={() => onChange(d - 1)}>
            Ημέρα {d}
          </button>
        ))}
      </div>
    </section>
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

/** Compact horizontal gauge: current value vs. a fixed max, e.g. current CHP thermal
 * draw against the plant's fixed heat_available_kw ceiling. */
function PowerGauge({ label, value, max, unit }: { label: string; value: number; max: number; unit: string }) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  return (
    <div className="gauge">
      <div className="gauge-head">
        <span className="gauge-label">{label}</span>
        <span className="gauge-value">
          {value.toFixed(0)}
          {unit} / {max.toLocaleString()}
          {unit}
        </span>
      </div>
      <div className="gauge-track">
        <div className="gauge-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

/** Thermal-screen deployment for the viewed simulation day, as a fraction of 24h —
 * the screen's automatic controller (see twin/climate_model.py) has no single
 * on/off "now" state, only how many hours it was closed that day. */
function ScreenStatusBadge({ hours }: { hours: number }) {
  const pct = (hours / 24) * 100;
  const state = pct >= 90 ? "Κλειστή" : pct <= 5 ? "Ανοιχτή" : "Μερικώς κλειστή";
  return (
    <div className="gauge">
      <div className="gauge-head">
        <span className="gauge-label">Θερμοκουρτίνα (προβαλλόμενη ημέρα)</span>
        <span className="gauge-value">
          {state} — {hours.toFixed(1)}/24h
        </span>
      </div>
      <div className="gauge-track">
        <div className="gauge-fill screen" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

/** Fan-pad engagement for the viewed simulation day, as a fraction of 24h -- same
 * caveat as ScreenStatusBadge: no single on/off "now" state, only hours engaged
 * that day (twin/climate_model.py: fan_pad_active = enabled and ach > vent_min_ach). */
function FanPadStatusBadge({ hours }: { hours: number }) {
  const pct = (hours / 24) * 100;
  return (
    <div className="gauge">
      <div className="gauge-head">
        <span className="gauge-label">Fan-pad ψύξη (προβαλλόμενη ημέρα)</span>
        <span className="gauge-value">{hours.toFixed(1)}/24h</span>
      </div>
      <div className="gauge-track">
        <div className="gauge-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

/** Static reference band over the selected run length, split at the model's own
 * fruiting_start_days/fruiting_ramp_days (twin/crop_model.py _fruit_partition_fraction) —
 * not a live "day N of N" progress bar, since a run always simulates the full
 * duration in one batch rather than advancing day-by-day. */
function CropPhaseTimeline({
  durationDays,
  fruitingStartDays,
  fruitingRampDays,
}: {
  durationDays: number;
  fruitingStartDays: number;
  fruitingRampDays: number;
}) {
  const vegEnd = Math.min(fruitingStartDays, durationDays);
  const rampEnd = Math.min(fruitingStartDays + fruitingRampDays, durationDays);
  const vegPct = (vegEnd / durationDays) * 100;
  const rampPct = ((rampEnd - vegEnd) / durationDays) * 100;
  const fullPct = 100 - vegPct - rampPct;
  return (
    <div className="phase-timeline">
      <span className="side-field-label">Φάσεις καλλιέργειας ({durationDays} μέρες)</span>
      <div className="phase-bar">
        <div
          className="phase-segment veg"
          style={{ width: `${vegPct}%` }}
          title={`Βλαστική ανάπτυξη: 0–${vegEnd.toFixed(0)} μέρες`}
        />
        <div
          className="phase-segment ramp"
          style={{ width: `${rampPct}%` }}
          title={`Έναρξη καρποφορίας: ${vegEnd.toFixed(0)}–${rampEnd.toFixed(0)} μέρες`}
        />
        <div
          className="phase-segment full"
          style={{ width: `${fullPct}%` }}
          title={`Πλήρης καρποφορία: ${rampEnd.toFixed(0)}–${durationDays} μέρες`}
        />
      </div>
      <div className="phase-legend">
        <span>
          <i className="dot veg" /> Βλαστική
        </span>
        <span>
          <i className="dot ramp" /> Έναρξη καρποφορίας
        </span>
        <span>
          <i className="dot full" /> Πλήρης καρποφορία
        </span>
      </div>
    </div>
  );
}

function Sparkline({ data, dataKey, color }: { data: DailyPoint[]; dataKey: keyof DailyPoint; color: string }) {
  return (
    <ResponsiveContainer width="100%" height={56}>
      <LineChart data={data} margin={{ top: 4, right: 4, left: 4, bottom: 0 }}>
        <Line
          type="monotone"
          dataKey={dataKey as string}
          stroke={color}
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

/** Compare-mode merges two runs by day-offset (index within each run), not
 * calendar date, since a baseline pinned from a different start_date/duration_days
 * would otherwise not align on the x-axis at all. */
const COMPARE_KEYS: (keyof DailyPoint)[] = [
  "temp_in_c",
  "temp_out_c",
  "rh_in_pct",
  "vpd_kpa",
  "fruit_fresh_yield_kg_m2",
  "heat_used_kw",
  "screen_closed_hours",
  "fan_pad_active_hours",
  "dehumidification_elec_kw",
  "ventilation_elec_kw",
  "recirculation_elec_kw",
  "fertigation_elec_kw",
  "irrigation_water_l_day",
  "drainage_water_l_day",
  "fertilizer_dosed_g_day",
  "fruit_set_pct",
];

function mergeForCompare(current: DailyPoint[], baseline: DailyPoint[]): Record<string, number>[] {
  const len = Math.max(current.length, baseline.length);
  const rows: Record<string, number>[] = [];
  for (let i = 0; i < len; i++) {
    const row: Record<string, number> = { day: i };
    for (const k of COMPARE_KEYS) {
      if (current[i]) row[`cur_${k}`] = current[i][k] as number;
      if (baseline[i]) row[`base_${k}`] = baseline[i][k] as number;
    }
    rows.push(row);
  }
  return rows;
}

interface ChartSeriesDef {
  dataKey: string;
  name: string;
  color: string;
  dashed?: boolean;
}

/** In compare mode, one metric becomes two lines (current + dashed baseline) sharing
 * the same color; otherwise it's just the plain single-run line. */
function buildSeries(keys: { key: string; name: string; color: string }[], compare: boolean): ChartSeriesDef[] {
  if (!compare) {
    return keys.map((k) => ({ dataKey: k.key, name: k.name, color: k.color }));
  }
  return keys.flatMap((k) => [
    { dataKey: `cur_${k.key}`, name: `${k.name} (τρέχον)`, color: k.color },
    { dataKey: `base_${k.key}`, name: `${k.name} (baseline)`, color: k.color, dashed: true },
  ]);
}

function ComparableChart({
  title,
  subtitle,
  unit,
  height,
  domain,
  data,
  xKey,
  viewedX,
  series,
}: {
  title: string;
  subtitle?: string;
  unit: string;
  height: number;
  domain?: [number, number];
  data: Record<string, unknown>[];
  xKey: string;
  viewedX?: string | number;
  series: ChartSeriesDef[];
}) {
  return (
    <section className="chart-card">
      <h2>{title}</h2>
      {subtitle && <p className="chart-card-subtitle">{subtitle}</p>}
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="var(--gridline)" vertical={false} />
          <XAxis
            dataKey={xKey}
            stroke="var(--muted)"
            tick={{ fontSize: 12 }}
            minTickGap={40}
            label={xKey === "day" ? { value: "Ημέρα", position: "insideBottomRight", offset: -4, fontSize: 11 } : undefined}
          />
          <YAxis stroke="var(--muted)" tick={{ fontSize: 12 }} unit={unit} width={56} domain={domain} />
          <Tooltip contentStyle={{ background: "var(--surface-1)", border: "1px solid var(--gridline)" }} />
          <Legend />
          {viewedX !== undefined && (
            <ReferenceLine x={viewedX} stroke="var(--amber)" strokeDasharray="3 3" strokeWidth={1.5} />
          )}
          {series.map((s) => (
            <Line
              key={s.dataKey}
              type="monotone"
              dataKey={s.dataKey}
              name={s.name}
              stroke={s.color}
              strokeWidth={2}
              strokeDasharray={s.dashed ? "5 3" : undefined}
              dot={false}
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </section>
  );
}

function downloadCsv(result: SimulationResult) {
  const headers = [
    "date",
    "temp_in_c",
    "temp_out_c",
    "co2_in_ppm",
    "rh_in_pct",
    "vpd_kpa",
    "fruit_fresh_yield_kg_m2",
    "heat_used_kw",
    "screen_closed_hours",
    "fan_pad_active_hours",
    "dehumidification_elec_kw",
    "ventilation_elec_kw",
    "recirculation_elec_kw",
    "fertigation_elec_kw",
    "irrigation_water_l_day",
    "drainage_water_l_day",
    "fertilizer_dosed_g_day",
    "fruit_set_pct",
  ] as const;
  const rows = result.daily_series.map((d) => headers.map((h) => d[h]).join(","));
  const csv = [headers.join(","), ...rows].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `greenhouse-simulation-${result.summary.duration_days}d.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

export default App;
