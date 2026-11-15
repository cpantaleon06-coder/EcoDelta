// Small labels that travel with every result: where the data came from, how strong the evidence is,
// how much of the study area and period had data, and that regions are approximate boxes.
// All render as spans so they can also sit inside the ranking buttons.
import { isDemoData, loadMeta, type Answers, type EvidenceClass, type Provenance, type Region, type RegionVariable } from '../dataClient';
import { fmt, fmtP, fmtPercent } from '../format';
import { P_Q_EFFECT } from '../copy';
import { useAsync } from '../useAsync';
import { coverage, evidenceLabel, sourceLine } from '../results';
import { Icon } from './Icon';

/** Header badge from meta.synthetic / meta.source; nothing while meta is loading or failed. */
export function DataBadge() {
  const { data: meta } = useAsync(loadMeta, []);
  if (!meta) return null;
  const demo = isDemoData(meta);
  return <span className={`data-badge ${demo ? 'data-badge--demo' : ''}`}>{demo ? 'DEMO DATA' : 'Real NASA data'}</span>;
}

export const SourceLine = ({ provenance }: { provenance?: Provenance }) => (
  <span className="source-line">{sourceLine(provenance)}</span>
);

/** "approximate study area" next to a region name whenever the region is a lat/lon box. */
export const AreaTag = ({ region }: { region: Pick<Region, 'kind'> }) =>
  region.kind === 'approximate_box' ? <span className="area-tag">approximate study area</span> : null;

/** Evidence class as symbol plus word (never color alone). */
export function Evidence({ cls, capped }: { cls?: EvidenceClass; capped?: boolean }) {
  const e = evidenceLabel(cls);
  return (
    <span className={`evidence evidence--${(cls ?? 'na').replace(' ', '-')}`}>
      <span aria-hidden="true" className="evidence__dots">
        {e.symbol}
      </span>
      {e.text}
      {capped && <span className="evidence__cap"> (lowered: low coverage)</span>}
    </span>
  );
}

/** Spatial and temporal coverage from answers.where.fixed_mask, with a visible warning when it is low. */
export function Coverage({ where, compact = false }: { where: Answers['where']; compact?: boolean }) {
  const c = coverage(where);
  if (!c) return <span className="coverage">Coverage: not available</span>;
  return (
    <span className={`coverage${compact ? ' coverage--compact' : ''}`}>
      <span>
        Coverage: {c.spatial}; {c.temporal}.
      </span>
      {c.warnings.length > 0 && (
        <span className="coverage__warn">
          <Icon name="no-data" size={14} /> Low coverage: {c.warnings.join(', ')}. Treat this result with extra care.
        </span>
      )}
    </span>
  );
}

/** p (this regional average), q (the map, after FDR) and effect size side by side, with one sentence on how they differ. */
export function ExpertsNote({ v }: { v: RegionVariable }) {
  const sig = v.answers.significance;
  const effect = v.magnitude?.standardized_change;
  return (
    <span className="experts">
      For experts: p {fmtP(sig.pvalue)}
      {sig.test ? ` (${sig.test}, one test on the regional average)` : ' (one test on the regional average)'}; q (map-level FDR):{' '}
      {fmtPercent(sig.cells_significant_after_fdr_fraction)} of the grid cells in this box are significant after FDR; effect
      size (standardized change): {effect == null ? 'not available' : `${fmt(effect)} typical monthly swings`}. {P_Q_EFFECT}
    </span>
  );
}
