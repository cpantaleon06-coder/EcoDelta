import { Area, CartesianGrid, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { RegionVariable } from '../dataClient';
import { displayTrend, yearTicks } from '../trendLine';
import { fmtSigned, fmtTick } from '../format';
import { reducedMotion } from '../viz';

interface Props {
  dates: string[];
  series: NonNullable<RegionVariable['series']>;
  slopePerDecade: number | null;
  ciPerDecade?: [number, number] | null;
  significant: boolean;
  unit: string;
  color: string;
  label: string;
  /** key and tooltip names for the monthly and 12-month lines, when they are not plain anomalies */
  names?: { a: string; m: string };
}

// SVG attributes cannot read CSS variables reliably, so the chart keeps its own copy of the tokens.
const INK = { rule: '#1b2f3a', axis: '#2b4655', muted: '#87a5ab', text: '#e4f1ef', panel: '#172c37' };
const FONT = "'Poppins', Arial, Helvetica, sans-serif";
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const monthLabel = (d: string) => `${MONTHS[Number(d.slice(5, 7)) - 1]} ${d.slice(0, 4)}`;
const NAMES: Record<string, string> = { a: 'Monthly anomaly', m: '12-month mean', t: 'Trend line' };

/** A short label drawn at the right end of a line (direct labelling instead of a legend lookup). */
const endLabel = (text: string, fill: string, last: number) =>
  function EndLabel(p: { index?: number; x?: number | string; y?: number | string }) {
    if (p.index !== last || p.x === undefined || p.y === undefined) return <g />;
    return (
      <text x={Number(p.x) + 6} y={Number(p.y)} dy={4} fill={fill} fontSize={12} fontFamily={FONT}>
        {text}
      </text>
    );
  };

export function TrendChart({ dates, series, slopePerDecade, ciPerDecade, significant, unit, color, label, names }: Props) {
  const tipNames = names ? { ...NAMES, ...names } : NAMES;
  const n = dates.length;
  const lastMean = series.running_mean_12.reduce<number>((k, v, i) => (v !== null ? i : k), -1);
  const data = dates.map((_, i) => ({
    i,
    a: series.anomaly[i],
    m: series.running_mean_12[i],
    t: slopePerDecade === null ? null : displayTrend(slopePerDecade, i, n),
    // slopes at both ends of the 95% CI, through the same mid-period point as the trend line
    f: ciPerDecade ? [displayTrend(ciPerDecade[0], i, n), displayTrend(ciPerDecade[1], i, n)].sort((x, y) => x - y) : null,
  }));
  const tick = { fill: INK.muted, fontSize: 12, fontFamily: FONT };
  return (
    <figure className="chart" style={{ '--var': color } as React.CSSProperties}>
      <div className="chart__plot" role="img" aria-label={label}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 10, right: 46, bottom: 4, left: 0 }}>
            <CartesianGrid stroke={INK.rule} vertical={false} />
            <XAxis
              dataKey="i"
              type="number"
              domain={[0, n - 1]}
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
              labelFormatter={(i) => monthLabel(dates[Number(i)] ?? '')}
              formatter={(v, name) =>
                Array.isArray(v) ? [`${fmtSigned(Number(v[0]))} to ${fmtSigned(Number(v[1]))}`, 'Slope range (95% CI)'] : [`${fmtSigned(Number(v))} ${unit}`, tipNames[String(name)] ?? name]
              }
              contentStyle={{ background: INK.panel, border: 'none', borderRadius: 8, fontSize: 13, lineHeight: 1.5, fontFamily: FONT, color: INK.text }}
              labelStyle={{ color: INK.muted }}
              cursor={{ stroke: INK.axis }}
            />
            {ciPerDecade && slopePerDecade !== null && (
              <Area dataKey="f" name="f" tooltipType="none" stroke="none" fill={INK.text} fillOpacity={0.07} isAnimationActive={false} activeDot={false} />
            )}
            <Line dataKey="a" name="a" stroke={color} strokeOpacity={0.3} strokeWidth={1} dot={false} isAnimationActive={false} connectNulls={false} />
            <Line
              dataKey="m"
              name="m"
              stroke={color}
              strokeWidth={2.75}
              dot={false}
              isAnimationActive={!reducedMotion()}
              animationDuration={900}
              connectNulls={false}
              label={endLabel('mean', color, lastMean)}
            />
            {slopePerDecade !== null && (
              <Line
                dataKey="t"
                name="t"
                stroke={INK.text}
                strokeWidth={significant ? 2 : 1.5}
                strokeDasharray={significant ? '8 4' : '2 4'}
                strokeOpacity={significant ? 0.95 : 0.6}
                dot={false}
                isAnimationActive={false}
                activeDot={false}
                label={endLabel('trend', INK.text, n - 1)}
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <figcaption className="chart__key">
        <span>
          <i className="key-line key-line--thin" style={{ borderColor: color }} aria-hidden="true" />{' '}
          {names?.a ?? 'Monthly anomaly (difference from the usual value for that month)'}
        </span>
        <span>
          <i className="key-line key-line--thick" style={{ borderColor: color }} aria-hidden="true" /> {names?.m ?? '12-month running mean'}
        </span>
        {slopePerDecade !== null && (
          <span>
            <i className={`key-line ${significant ? 'key-line--dash' : 'key-line--dot'}`} aria-hidden="true" />{' '}
            {significant ? 'Trend line' : 'Trend estimate, not significant'} (drawn only to show the slope)
          </span>
        )}
        {ciPerDecade && slopePerDecade !== null && (
          <span>
            <i className="key-fan" aria-hidden="true" /> Slopes within the 95% CI
          </span>
        )}
      </figcaption>
    </figure>
  );
}
