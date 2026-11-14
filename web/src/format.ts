// Display formatting only: numbers arrive already computed and rounded by the engine.
import type { RankedVariable } from './dataClient';

const MINUS = '−';

/**
 * Number with `sig` significant digits (trailing zeros kept, so 0.5004 -> "0.500" like the engine's sentences),
 * real minus sign, optional leading "+". null -> "n/a".
 */
export function fmt(x: number | null | undefined, sig = 3, signed = false): string {
  if (x === null || x === undefined || !Number.isFinite(x)) return 'n/a';
  if (x === 0) return '0';
  let s = x.toPrecision(sig);
  if (s.includes('e')) s = Math.abs(x) >= 1 ? String(Math.round(x)) : x.toExponential(sig - 1);
  if (x < 0) return MINUS + s.slice(1);
  return signed ? `+${s}` : s;
}

export const fmtSigned = (x: number | null | undefined, sig = 3) => fmt(x, sig, true);

/** Axis ticks: short, no trailing zeros (0.60 -> "0.6"). */
export const fmtTick = (x: number) => fmt(Number(x.toPrecision(2)), 2).replace(/(\.\d*?)0+$/, '$1').replace(/\.$/, '');

/** p-values: "< 0.001" below that, otherwise 2 significant digits. */
export function fmtP(p: number | null | undefined): string {
  if (p === null || p === undefined || !Number.isFinite(p)) return 'n/a';
  return p < 0.001 ? '< 0.001' : `= ${fmt(p, 2)}`;
}

export const fmtLatLon = (lat: number, lon: number) =>
  `${Math.abs(lat)}°${lat < 0 ? 'S' : 'N'}, ${Math.abs(lon)}°${lon < 0 ? 'W' : 'E'}`;

export const fmtPercent = (fraction: number | null | undefined) =>
  fraction === null || fraction === undefined ? 'n/a' : `${Math.round(fraction * 100)}%`;

/** "autocorrelation_handling" -> "Autocorrelation handling" */
export const humanizeKey = (k: string) =>
  (k.charAt(0).toUpperCase() + k.slice(1)).replace(/_/g, ' ').replace(/\b(ci|fdr|ols)\b/gi, (m) => m.toUpperCase());

/** Plain text for a value from meta.methods (string, number, list or small object), shown as is. */
export function describeValue(v: unknown): string {
  if (v === null || v === undefined) return 'n/a';
  if (Array.isArray(v)) {
    const isMonthPair = v.length === 2 && v.every((x) => typeof x === 'string' && /^\d{4}-\d{2}$/.test(x));
    return isMonthPair ? `${v[0]} to ${v[1]}` : v.map(describeValue).join(', ');
  }
  if (typeof v === 'object') return Object.entries(v).map(([k, x]) => `${humanizeKey(k)}: ${describeValue(x)}`).join('; ');
  return String(v);
}

/** Badge text for a result; tier 2 means the engine had too little data. */
export function badgeFor(r: Pick<RankedVariable, 'tier' | 'significant'>) {
  if (r.tier === 2) return { text: 'Not enough data', cls: 'badge--none' };
  return r.significant ? { text: 'Significant', cls: 'badge--sig' } : { text: 'Not significant', cls: 'badge--nosig' };
}
