import type { IconName } from './components/Icon';
// Small display helpers for the graphics. They only pick and map values that are
// already in the data files; nothing here estimates or averages anything.
import { colorFor } from './mapScale';

/** Identity color of each variable (kept in sync with --var-* in styles/tokens.css). */
export const VAR_COLORS: Record<string, string> = {
  t2m: '#a8e06c',
  precip: '#6b9af0',
  evap: '#2ec4b6',
  runoff_surface: '#5ccaf2',
  soil_moisture_0_10cm: '#3ddc97',
};
export const varColor = (id: string) => VAR_COLORS[id] ?? '#b3cbcc';

/** n + 1 class edges of the symmetric map scale, from -max to +max (the classes colorFor uses). */
export const classEdges = (max: number, n = 9) => Array.from({ length: n + 1 }, (_, k) => -max + (2 * max * k) / n);

export interface YearValue {
  year: number;
  value: number;
}

/**
 * One value per calendar year: the trailing 12-month running mean at each December, as exported.
 * Years without a December value (a partial last year, or missing data) are left out.
 */
export function yearlyValues(dates: string[], runningMean12: (number | null)[]): YearValue[] {
  return dates.flatMap((d, i) => {
    const v = runningMean12[i];
    return d.endsWith('-12') && v !== null && v !== undefined && Number.isFinite(v) ? [{ year: Number(d.slice(0, 4)), value: v }] : [];
  });
}

/** SVG polyline points for a sparkline in a w x h box, scaled to min..max (1px inset); a flat series sits in the middle. */
export function sparkPoints(values: number[], w: number, h: number): string {
  const lo = Math.min(...values);
  const hi = Math.max(...values);
  const y = (v: number) => (hi === lo ? h / 2 : h - 1 - ((v - lo) / (hi - lo)) * (h - 2));
  return values.map((v, i) => `${((i / Math.max(1, values.length - 1)) * w).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
}

/** Stripe colors on the map's own palette, symmetric around zero so a zero year gets the neutral middle. */
export function stripeColors(values: number[], palette: string[]): string[] {
  const max = Math.max(...values.map(Math.abs)) || 1;
  return values.map((v) => colorFor(v, max, palette));
}

export const reducedMotion = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;

const VAR_ICONS: Record<string, IconName> = {
  t2m: 'temperature',
  precip: 'precipitation',
  evap: 'evaporation',
  runoff_surface: 'runoff',
  soil_moisture_0_10cm: 'soil',
};
/** Icon for a variable id from the data, or undefined for a variable this set has no drawing for. */
export const varIcon = (id: string): IconName | undefined => VAR_ICONS[id];
