// Display rules for result metadata (evidence, coverage, sources). They only pick, label and compare values
// that are already in the data files against fixed thresholds published by the engine; nothing is estimated.
import type { Answers, ComparePair, CompareFile, EvidenceClass, Provenance } from './dataClient';

export const NA = 'not available';

// symbol plus word: the evidence class is never shown by color alone
const EVIDENCE: Record<EvidenceClass, { symbol: string; text: string }> = {
  strong: { symbol: '●●●', text: 'Strong evidence' },
  moderate: { symbol: '●●○', text: 'Moderate evidence' },
  weak: { symbol: '●○○', text: 'Weak evidence' },
  none: { symbol: '○○○', text: 'No evidence of a trend' },
  'insufficient data': { symbol: '···', text: 'Insufficient data' },
};
export const evidenceLabel = (cls: EvidenceClass | undefined) => (cls ? EVIDENCE[cls] : { symbol: '', text: `Evidence: ${NA}` });

/** Engine thresholds: the evidence class is capped below 30% box coverage (meta.methods.evidence_classes);
 * a trend needs at least 80% of months (meta.methods.data_requirement). */
export const LOW_SPATIAL = 0.3;
export const LOW_TEMPORAL = 0.8;

const pct = (x: number) => `${Math.round(x * 100)}%`;

/** Coverage of a regional result from answers.where.fixed_mask; null when the file has no fixed mask. */
export function coverage(where: Answers['where']) {
  const fm = where.fixed_mask;
  if (!fm) return null;
  const temporal = fm.n_months ? fm.n_valid_months / fm.n_months : 0;
  const warnings = [
    fm.covered_fraction < LOW_SPATIAL && `only ${pct(fm.covered_fraction)} of the study area has data`,
    temporal < LOW_TEMPORAL && `only ${fm.n_valid_months} of ${fm.n_months} months have data`,
  ].filter((w): w is string => !!w);
  return {
    spatial: `${fm.n_cells} of ${where.n_box_cells} grid cells, ${pct(fm.covered_fraction)} of the study area`,
    temporal: `${fm.n_valid_months} of ${fm.n_months} months`,
    warnings,
  };
}

/** "Source: MERRA-2 version 5.12.4, 2001-01 to 2025-09" from the variable's provenance. */
export function sourceLine(p: Provenance | undefined): string {
  if (!p) return `Source: ${NA}`;
  const product = p.product_short_name ?? NA;
  const version = p.version ? `version ${p.version}` : `version ${NA}`;
  const period = p.period ? `${p.period[0]} to ${p.period[1]}` : `period ${NA}`;
  return `Source: ${product}, ${version}, ${period}`;
}

export interface Signal {
  name: string;
  evidence?: EvidenceClass;
  direction: Answers['what']['direction'];
}

/** Fixed rule: list variables with moderate or strong evidence and a direction, in the given order. */
export function signalsTogether(rows: Signal[]): string {
  const found = rows
    .filter((r) => (r.evidence === 'strong' || r.evidence === 'moderate') && r.direction !== 'none detected')
    .map((r) => `${r.name.toLowerCase()}: ${r.direction === 'increase' ? 'increasing' : 'decreasing'}`);
  return found.length ? `Signals found together: ${found.join('; ')}.` : 'No variable here has moderate or strong evidence of a trend.';
}
export const NOT_CAUSAL = 'This shows what changed together, not what caused what.';

/** The pair for two regions in either order; the result keeps the file's order (D = region_a minus region_b). */
export const findPair = (file: CompareFile, a: string, b: string): ComparePair | undefined =>
  file.pairs.find((p) => (p.region_a === a && p.region_b === b) || (p.region_a === b && p.region_b === a));
