interface ParamSliderProps {
  label: string;
  value: number;
  unit: string;
  min: number;
  max: number;
  step: number;
  optimal?: [number, number];
  note?: string;
  onChange: (value: number) => void;
}

/** Slider with an optional highlighted "optimal" band, in the style of the
 * earlier greenhouse mockup — value pill turns amber outside the band. */
export function ParamSlider({ label, value, unit, min, max, step, optimal, note, onChange }: ParamSliderProps) {
  const inOptimal = optimal ? value >= optimal[0] && value <= optimal[1] : true;
  const pct = ((value - min) / (max - min)) * 100;
  const optL = optimal ? ((optimal[0] - min) / (max - min)) * 100 : 0;
  const optR = optimal ? ((optimal[1] - min) / (max - min)) * 100 : 100;

  return (
    <div className="param-slider">
      <div className="param-slider-head">
        <span className="param-slider-label">{label}</span>
        <span className={`param-slider-value ${inOptimal ? "in-optimal" : "out-optimal"}`}>
          {value}
          {unit}
        </span>
      </div>
      <div className="param-slider-track">
        {optimal && (
          <div className="param-slider-optimal-band" style={{ left: `${optL}%`, width: `${optR - optL}%` }} />
        )}
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(parseFloat(e.target.value))}
          style={{
            background: `linear-gradient(to right, ${inOptimal ? "var(--series-4)" : "var(--amber)"} ${pct}%, var(--gridline) ${pct}%)`,
          }}
        />
      </div>
      {optimal && (
        <div className="param-slider-range">
          <span>
            {min}
            {unit}
          </span>
          <span className="param-slider-optimal-label">
            βέλτιστο {optimal[0]}–{optimal[1]}
            {unit}
          </span>
          <span>
            {max}
            {unit}
          </span>
        </div>
      )}
      {note && <p className="param-slider-note">ⓘ {note}</p>}
    </div>
  );
}
