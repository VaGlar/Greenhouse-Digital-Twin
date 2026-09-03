export type ZoneKey = "climate" | "humidity" | "crop";

interface ZoneHotspot {
  zone: ZoneKey;
  label: string;
  /** Hit-area rect, in the 0..640 x 0..280 viewBox. */
  x: number;
  y: number;
  w: number;
  h: number;
}

interface Pin {
  x: number;
  y: number;
  label: string;
  value: string;
  anchor?: "start" | "middle" | "end";
}

const HOTSPOTS: ZoneHotspot[] = [
  { zone: "climate", label: "Κάλυμμα & δομή", x: 30, y: 18, w: 580, h: 60 },
  { zone: "humidity", label: "Θερμοκουρτίνα", x: 90, y: 96, w: 460, h: 20 },
  { zone: "climate", label: "Αέρας / κλίμα", x: 250, y: 125, w: 300, h: 70 },
  { zone: "crop", label: "Καλλιέργεια", x: 90, y: 190, w: 460, h: 56 },
  // Drawn after the wide cover hotspot above, so these two win clicks in the
  // small area around each vent icon.
  { zone: "humidity", label: "Αριστερός αεριστήρας", x: 135, y: 15, w: 55, h: 30 },
  { zone: "humidity", label: "Δεξιός αεριστήρας & αφύγρανση", x: 450, y: 15, w: 55, h: 30 },
];

interface GreenhouseSchematicProps {
  activeZone: ZoneKey | null;
  onZoneClick: (zone: ZoneKey) => void;
  outdoorTempC: number | null;
  indoorTempC: number | null;
  rhPct: number | null;
  vpdKpa: number | null;
  co2Ppm: number | null;
  /** Season-average % of hours the screen was deployed — fully automatic, no user control. */
  screenDeployedPct: number | null;
  dehumidSetpointPct: number;
  yieldKgM2: number | null;
}

/** Static cross-section drawing (arch, cover, thermal screen, gutter, vents)
 * with clickable zone hotspots and live-value pins layered on top. The
 * geometry mirrors the arch shape in the Geothermiki S192G vendor quote —
 * see docs/assumptions/geometry-and-chp.md. */
export function GreenhouseSchematic({
  activeZone,
  onZoneClick,
  outdoorTempC,
  indoorTempC,
  rhPct,
  vpdKpa,
  co2Ppm,
  screenDeployedPct,
  dehumidSetpointPct,
  yieldKgM2,
}: GreenhouseSchematicProps) {
  const fmt = (v: number | null, digits = 1, unit = "") =>
    v === null ? "–" : `${v.toFixed(digits)}${unit}`;

  const pins: Pin[] = [
    { x: 320, y: 11, label: "Έξω", value: fmt(outdoorTempC, 1, "°C"), anchor: "middle" },
    { x: 250, y: 150, label: "Μέσα", value: fmt(indoorTempC, 1, "°C"), anchor: "middle" },
    { x: 400, y: 145, label: "RH", value: fmt(rhPct, 0, "%"), anchor: "start" },
    { x: 400, y: 163, label: "VPD", value: fmt(vpdKpa, 2, " kPa"), anchor: "start" },
    { x: 400, y: 181, label: "CO₂", value: fmt(co2Ppm, 0, " ppm"), anchor: "start" },
    {
      x: 100,
      y: 90,
      label: "Κλειστή",
      value: screenDeployedPct === null ? "αυτόματα (νύχτα/ζέστη/κρύο)" : `${screenDeployedPct.toFixed(0)}% του χρόνου`,
      anchor: "start",
    },
    { x: 455, y: 52, label: "Στόχος RH (είσοδος)", value: `${dehumidSetpointPct.toFixed(0)}%`, anchor: "start" },
    { x: 320, y: 250, label: "Marketable yield μέχρι τώρα", value: fmt(yieldKgM2, 2, " kg/m²"), anchor: "middle" },
  ];

  return (
    <figure className="schematic-figure">
      <svg viewBox="0 0 640 268" role="img" aria-label="Διατομή θερμοκηπίου με ζωντανές τιμές" className="schematic-svg">
        {/* Gutter / foundation line */}
        <line x1="30" y1="230" x2="610" y2="230" className="schematic-structure" />

        {/* Arch cover, two bays, matching the vendor quote's arch shape */}
        <path
          d="M 30 230 L 30 90 Q 30 20 150 20 L 490 20 Q 610 20 610 90 L 610 230"
          className="schematic-cover"
        />

        {/* Thermal screen, horizontal, below the arch */}
        <line x1="60" y1="106" x2="580" y2="106" className="schematic-screen" strokeDasharray="6 5" />

        {/* Roof vents */}
        <path d="M 150 22 L 175 22 L 163 40 Z" className="schematic-vent" />
        <path d="M 465 22 L 490 22 L 478 40 Z" className="schematic-vent" />

        {/* Crop rows along the gutter line */}
        {[110, 200, 320, 440, 530].map((cx) => (
          <g key={cx} className="schematic-plant">
            <line x1={cx} y1="230" x2={cx} y2="200" />
            <circle cx={cx} cy="196" r="7" />
          </g>
        ))}

        {/* Zone hotspots (transparent hit areas) */}
        {HOTSPOTS.map((h, i) => (
          <rect
            key={i}
            x={h.x}
            y={h.y}
            width={h.w}
            height={h.h}
            className={`schematic-hotspot ${activeZone === h.zone ? "active" : ""}`}
            onClick={() => onZoneClick(h.zone)}
          >
            <title>{h.label}</title>
          </rect>
        ))}

        {/* Live pins */}
        {pins.map((p, i) => (
          <text key={i} x={p.x} y={p.y} textAnchor={p.anchor ?? "start"} className="schematic-pin">
            <tspan className="schematic-pin-label">{p.label} </tspan>
            <tspan className="schematic-pin-value">{p.value}</tspan>
          </text>
        ))}
      </svg>
      <figcaption>Διατομή θερμοκηπίου (τόξο OptiClima) — κάντε κλικ σε μια ζώνη για μετάβαση στις παραμέτρους της.</figcaption>
    </figure>
  );
}
