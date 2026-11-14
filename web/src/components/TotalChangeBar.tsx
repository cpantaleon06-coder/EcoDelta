import { barGeometry } from '../trendLine';
import { fmt, fmtSigned } from '../format';

interface Props {
  value: number;
  ci: [number, number];
  unit: string;
  years: number;
  color: string;
}

/** Total change over the period as a bar from zero with its 95% CI whisker. Numbers come from the data. */
export function TotalChangeBar({ value, ci, unit, years, color }: Props) {
  return (
    <figure className="tcb">
      <figcaption className="tcb__label">
        Total change over {fmt(years)} years:{' '}
        <strong>
          {fmtSigned(value)} {unit}
        </strong>{' '}
        <span className="muted">
          (95% CI {fmtSigned(ci[0])} to {fmtSigned(ci[1])})
        </span>
      </figcaption>
      <CiBar value={value} ci={ci} color={color} />
      <div className="tcb__axis" aria-hidden="true">
        <span>less</span>
        <span>0</span>
        <span>more</span>
      </div>
    </figure>
  );
}

/** Bar from zero to the value with the 95% CI as a whisker; the numbers are always shown next to it in text. */
function CiBar({ value, ci, color }: { value: number; ci: [number, number]; color: string }) {
  const g = barGeometry(value, ci[0], ci[1]);
  return (
    <div className="cibar" aria-hidden="true">
      <span className="cibar__zero" />
      <span className="cibar__bar" style={{ left: `${g.barStart}%`, width: `${g.barEnd - g.barStart}%`, background: color }} />
      <span className="cibar__ci" style={{ left: `${g.ciStart}%`, width: `${g.ciEnd - g.ciStart}%` }} />
    </div>
  );
}
