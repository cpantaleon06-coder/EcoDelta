import { useState } from 'react';
import { loadRegionDetail, loadScreening, type RankedVariable, type Region, type Variable } from '../dataClient';
import { useAsync } from '../useAsync';
import { fmt, fmtSigned } from '../format';
import { varColor, yearlyValues, varIcon } from '../viz';
import { EVIDENCE_LEGEND } from '../copy';
import { ErrorBox, Loading } from './Status';
import { Spark } from './ui';
import { Icon } from './Icon';
import { CiBar } from './TotalChangeBar';
import { AreaTag, Coverage, Evidence, SourceLine } from './ResultMeta';

/** Arrow only for a significant trend; anything else must not look like a finding. */
export function Direction({ r }: { r: Pick<RankedVariable, 'significant' | 'verdict' | 'tier'> }) {
  if (r.significant && r.verdict === 'increasing')
    return (
      <span className="dir dir--up">
        <Icon name="increasing" size={16} /> Increasing
      </span>
    );
  if (r.significant && r.verdict === 'decreasing')
    return (
      <span className="dir dir--down">
        <Icon name="decreasing" size={16} /> Decreasing
      </span>
    );
  return <span className="dir dir--none">{r.tier === 2 ? 'No estimate' : 'No clear trend'}</span>;
}

type Sort = 'evidence' | 'magnitude';

interface Props {
  region: Region;
  period: { start: string; end: string };
  variables: Variable[];
  selectedVar: string;
  onSelect: (variable: string) => void;
}

export function RankingPanel({ region, period, variables, selectedVar, onSelect }: Props) {
  const [sort, setSort] = useState<Sort>('evidence');
  const { data, error } = useAsync(() => loadScreening(region.id), [region.id]);
  // series, evidence and coverage per variable; the cards still work without it
  const detail = useAsync(() => loadRegionDetail(region.id), [region.id]);
  const d = detail.data?.region.id === region.id ? detail.data : undefined;
  // the two orderings come from the engine; without them, keep the file's ranking order
  const order = data && (sort === 'evidence' ? data.by_evidence : data.by_magnitude);
  const rows = data
    ? (order ?? data.ranking.map((r) => r.variable)).flatMap((id) => data.ranking.filter((r) => r.variable === id))
    : [];
  return (
    <>
      <h2 className="panel__title">
        <Icon name="ranking" size={22} className="title-icon" />
        What changed across {region.phrase}? <AreaTag region={region} />
      </h2>
      <p className="panel__period">
        {period.start} to {period.end}
      </p>
      <div className="sort" role="group" aria-label="Order the variables">
        {(['evidence', 'magnitude'] as const).map((s) => (
          <button key={s} type="button" className="sort__btn" aria-pressed={sort === s} onClick={() => setSort(s)}>
            By {s}
          </button>
        ))}
      </div>
      {data && !order && <p className="panel__hint">This ordering is not available in the data; showing the file order.</p>}
      <p className="panel__hint">{EVIDENCE_LEGEND}</p>
      {error ? (
        <ErrorBox error={error} />
      ) : !data || data.region_id !== region.id ? (
        <Loading label="Loading ranking…" minHeight={300} />
      ) : (
        <ol className="ranking" key={`${region.id}-${sort}`}>
          {rows.map((r, i) => {
            const finding = r.significant && r.tier === 0;
            const rv = d?.variables[r.variable];
            const years = rv?.series && d ? yearlyValues(d.dates, rv.series.running_mean_12) : [];
            const rank = (sort === 'evidence' ? r.rank : r.rank_by_magnitude) ?? i + 1;
            return (
              <li key={r.variable} style={{ '--i': i } as React.CSSProperties}>
                <button
                  type="button"
                  className={`rank-row ${finding ? '' : 'rank-row--muted'}`}
                  aria-current={r.variable === selectedVar ? 'true' : undefined}
                  onClick={() => onSelect(r.variable)}
                  style={{ '--var': varColor(r.variable) } as React.CSSProperties}
                >
                  <span className="rank-row__rank" aria-label={`Rank ${rank} by ${sort}`}>
                    {rank}
                  </span>
                  <span className="rank-row__body">
                    <span className="rank-row__name">
                      {varIcon(r.variable) && <Icon name={varIcon(r.variable)!} size={18} className="title-icon" />}
                      {r.name}
                    </span>
                    <span className="rank-row__meta">
                      <Direction r={r} />
                      <Evidence cls={r.evidence_class ?? rv?.evidence?.class} capped={rv?.evidence?.capped_by_coverage} />
                    </span>
                    {r.slope_per_decade !== null && r.ci_per_decade ? (
                      <span className="rank-row__mag">
                        <span className="rank-row__value">
                          Magnitude:{' '}
                          <strong>
                            {fmtSigned(r.slope_per_decade)} {r.public_unit}
                          </strong>{' '}
                          per decade (95% CI {fmtSigned(r.ci_per_decade[0])} to {fmtSigned(r.ci_per_decade[1])})
                          {r.standardized_change != null && <>; effect size {fmt(r.standardized_change)}</>}
                        </span>
                        <CiBar value={r.slope_per_decade} ci={r.ci_per_decade} color={varColor(r.variable)} />
                      </span>
                    ) : (
                      <span className="rank-row__value">Magnitude: not available</span>
                    )}
                    {rv && <Coverage where={rv.answers.where} compact />}
                    <SourceLine provenance={variables.find((v) => v.id === r.variable)?.provenance} />
                  </span>
                  <Spark years={years} />
                </button>
              </li>
            );
          })}
        </ol>
      )}
    </>
  );
}
