import { fmtTick } from '../format';
import { classEdges } from '../viz';

interface Props {
  palette: string[];
  max: number;
  unit: string;
  period: { start: string; end: string };
}

export function MapLegend({ palette, max, unit, period }: Props) {
  const end = palette[palette.length - 1];
  const edges = classEdges(max, palette.length);
  return (
    <figure className="legend" aria-label="Map legend">
      <figcaption className="legend__title">
        Trend per decade, {period.start} to {period.end} <span className="legend__unit">({unit} per decade)</span>
      </figcaption>
      <div className="legend__bar" aria-hidden="true">
        {palette.map((c) => (
          <span key={c} style={{ background: c }} />
        ))}
      </div>
      <ol className="legend__ticks" aria-label="Class breakpoints">
        {edges.map((e, k) => (
          <li key={k} style={{ left: `${(100 * k) / palette.length}%` }}>
            {k === 0 ? '≤' : k === edges.length - 1 ? '≥' : ''}
            {fmtTick(e)}
          </li>
        ))}
      </ol>
      <p className="legend__ends">
        <span>▼ decrease</span>
        <span>increase ▲</span>
      </p>
      <ul className="legend__read" aria-label="How to read the map">
        <li>
          <span style={{ color: end }} aria-hidden="true">●</span>
          <span>bright, dotted</span>
          <span>significant after correcting for many tests (FDR)</span>
        </li>
        <li>
          <span style={{ color: end, opacity: 0.62 }} aria-hidden="true">○</span>
          <span>faded</span>
          <span>not significant</span>
        </li>
        <li>
          <span aria-hidden="true">·</span>
          <span>blank</span>
          <span>no data or too little data</span>
        </li>
      </ul>
    </figure>
  );
}
