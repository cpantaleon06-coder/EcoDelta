import type { Meta, Region, RegionVariable, Variable } from '../dataClient';
import { fmtSigned } from '../format';
import { coverage } from '../results';
import { Coverage, Evidence } from './ResultMeta';

interface Props {
  v: RegionVariable;
  variable: Variable;
  region: Region;
  meta: Meta;
}

const str = (x: unknown) => (typeof x === 'string' ? x : undefined);

/** Five labelled parts, each built from the data files and the variable catalog text. */
export function ResearchNote({ v, variable, region, meta }: Props) {
  const hm = v.answers.how_much;
  const unit = variable.public_unit;
  const stats = variable.provenance?.statistics ?? meta.methods;
  const autocorrelation = str(stats.autocorrelation_note) ?? str(meta.methods.autocorrelation_note);
  const cap = str((meta.methods.evidence_classes as Record<string, unknown> | undefined)?.coverage_cap);
  const cov = coverage(v.answers.where);
  const resolution = variable.provenance?.grid.resolution_deg ?? meta.grid.resolution_deg;
  const warnings = [...new Set([...(v.report?.warnings ?? []), ...v.answers.significance.warnings])];
  return (
    <details className="research-note">
      <summary>Research note</summary>
      <dl>
        <dt>Finding</dt>
        <dd>{v.sentence}</dd>
        <dt>Evidence</dt>
        <dd>
          {hm.slope_per_decade === null
            ? 'Slope per decade: not available.'
            : `Slope ${fmtSigned(hm.slope_per_decade)} ${unit} per decade (95% CI ${hm.ci_per_decade ? `${fmtSigned(hm.ci_per_decade[0])} to ${fmtSigned(hm.ci_per_decade[1])}` : 'not available'}).`}{' '}
          Evidence class: <Evidence cls={v.evidence?.class} capped={v.evidence?.capped_by_coverage} />
        </dd>
        <dt>Coverage</dt>
        <dd>
          <Coverage where={v.answers.where} />
        </dd>
        <dt>Limitations</dt>
        <dd>
          <ul>
            <li>Resolution: {resolution !== undefined ? `${resolution} x ${resolution} degree grid cells` : 'not available'}.</li>
            {autocorrelation && <li>Month-to-month memory (autocorrelation): {autocorrelation}.</li>}
            {cov && cov.warnings.length > 0 && <li>Coverage is low: {cov.warnings.join(', ')}.</li>}
            {v.evidence?.capped_by_coverage && cap && <li>The evidence class was lowered: {cap}.</li>}
            {variable.caveats.map((c) => (
              <li key={c}>{c}</li>
            ))}
            {warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </dd>
        <dt>What we cannot conclude</dt>
        <dd>
          <ul>
            <li>What caused the change: this is a trend in one variable, not an explanation.</li>
            <li>
              Anything about a whole country: {region.name} here is {region.display_note ? `an ${region.display_note}` : 'a latitude and longitude box'}.
            </li>
            <li>
              What happens next: it describes {meta.period.start} to {meta.period.end} only and is not a forecast.
            </li>
          </ul>
        </dd>
      </dl>
    </details>
  );
}
