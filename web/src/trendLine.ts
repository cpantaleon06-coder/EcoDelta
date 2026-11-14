// Display-only trend line. The slope comes from the engine report; nothing is fitted here.
// The anomalies are deviations from the average over the whole period, so the line is drawn through
// zero at the middle of the period. Only its slope carries meaning.

/** Value of the display trend line at month index i of n months, for a slope given per decade. */
export function displayTrend(slopePerDecade: number, i: number, n: number): number {
  const yearsFromMiddle = (i - (n - 1) / 2) / 12;
  return (slopePerDecade * yearsFromMiddle) / 10;
}

/** Month indexes of the January ticks to label on the time axis (every `everyYears` years). */
export function yearTicks(dates: string[], everyYears = 5): number[] {
  return dates.flatMap((d, i) => (d.endsWith('-01') && Number(d.slice(0, 4)) % everyYears === 0 ? [i] : []));
}

/**
 * Positions (0..100 % of the bar width) for a total-change bar with its CI whisker, zero in the middle.
 * The scale is symmetric and leaves 10% headroom so the whisker never touches the edge.
 */
export function barGeometry(value: number, ciLow: number, ciHigh: number) {
  const scale = Math.max(Math.abs(ciLow), Math.abs(ciHigh), Math.abs(value)) * 1.1 || 1;
  const pos = (x: number) => 50 + (50 * x) / scale;
  return {
    barStart: Math.min(50, pos(value)),
    barEnd: Math.max(50, pos(value)),
    ciStart: pos(Math.min(ciLow, ciHigh)),
    ciEnd: pos(Math.max(ciLow, ciHigh)),
    value: pos(value),
  };
}
