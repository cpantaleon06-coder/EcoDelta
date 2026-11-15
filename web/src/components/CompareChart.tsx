import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { yearTicks } from '../trendLine';
import { fmtSigned, fmtTick } from '../format';

interface Series {
  name: string;
  values: (number | null)[];
}
interface Props {
  dates: string[];
  a: Series;
  b: Series;
  unit: string;
  color: string;
  label: string;
}

// same chart tokens as TrendChart (SVG attributes cannot read CSS variables reliably)
const INK = { rule: '#1b2f3a', axis: '#2b4655', muted: '#87a5ab', text: '#e4f1ef', panel: '#172c37' };
const FONT = "'Poppins', Arial, Helvetica, sans-serif";

/** The two regions' exported 12-month running means on one axis: A solid in the variable color, B dashed. */
export function CompareChart({ dates, a, b, unit, color, label }: Props) {
  const data = dates.map((d, i) => ({ i, d, a: a.values[i], b: b.values[i] }));
  const tick = { fill: INK.muted, fontSize: 12, fontFamily: FONT };
  return (
    <figure className="chart">
      <div className="chart__plot" role="img" aria-label={label}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 10, right: 16, bottom: 4, left: 0 }}>
            <CartesianGrid stroke={INK.rule} vertical={false} />
            <XAxis
              dataKey="i"
              type="number"
              domain={[0, dates.length - 1]}
              ticks={yearTicks(dates)}
              tickFormatter={(i: number) => dates[i]?.slice(0, 4) ?? ''}
              tick={tick}
              stroke={INK.axis}
            />
            <YAxis
              width={56}
              tick={tick}
              tickFormatter={fmtTick}
              stroke={INK.axis}
              label={{ value: unit, angle: -90, position: 'insideLeft', fill: INK.muted, fontSize: 12, dy: 20 }}
            />
            <ReferenceLine y={0} stroke={INK.muted} strokeOpacity={0.6} />
            <Tooltip
              labelFormatter={(i) => dates[Number(i)] ?? ''}
              formatter={(v, name) => [`${fmtSigned(Number(v))} ${unit}`, name === 'a' ? a.name : b.name]}
              contentStyle={{ background: INK.panel, border: 'none', borderRadius: 8, fontSize: 13, lineHeight: 1.5, fontFamily: FONT, color: INK.text }}
              labelStyle={{ color: INK.muted }}
              cursor={{ stroke: INK.axis }}
            />
            <Line dataKey="a" stroke={color} strokeWidth={2.5} dot={false} isAnimationActive={false} connectNulls={false} />
            <Line dataKey="b" stroke={INK.text} strokeWidth={2} strokeDasharray="6 4" dot={false} isAnimationActive={false} connectNulls={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <figcaption className="chart__key">
        <span>
          <i className="key-line key-line--thick" style={{ borderColor: color }} aria-hidden="true" /> {a.name}: 12-month
          running mean of the anomaly
        </span>
        <span>
          <i className="key-line key-line--dash" aria-hidden="true" /> {b.name}: 12-month running mean of the anomaly
        </span>
      </figcaption>
    </figure>
  );
}
