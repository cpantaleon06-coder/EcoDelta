import { fmtTick } from '../format';
import { classEdges } from '../viz';
import { Icon } from './Icon';

interface Props {
  palette: string[];
  max: number;
  unit: string;
  period: { start: string; end: string };
  /** display_note of the selected region, when it is an approximate box */
  areaNote?: string;
}

export function MapLegend({ palette, max, unit, period, areaNote }: Props) {
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
        <span>
          <Icon name="decreasing" size={14} /> decrease
        </span>
        <span>
          increase <Icon name="increasing" size={14} />
        </span>
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
          <span>no data or not applicable (the basemap shows through)</span>
        </li>
        {areaNote && (
          <li>
            <span aria-hidden="true">▭</span>
            <span>outline</span>
            <span>selected region: {areaNote}</span>
          </li>
        )}
      </ul>
    </figure>
  );
}
