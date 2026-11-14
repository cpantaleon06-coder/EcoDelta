import { loadRegionDetail, loadScreening, type RankedVariable, type Region } from '../dataClient';
import { useAsync } from '../useAsync';
import { fmtSigned } from '../format';
import { varColor, yearlyValues, varIcon } from '../viz';
import { ErrorBox, Loading } from './Status';
import { Spark } from './ui';
import { Icon } from './Icon';
import { StatusBadge } from './StatusBadge';

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

interface Props {
  region: Region;
  period: { start: string; end: string };
  selectedVar: string;
  onSelect: (variable: string) => void;
}

export function RankingPanel({ region, period, selectedVar, onSelect }: Props) {
  const { data, error } = useAsync(() => loadScreening(region.id), [region.id]);
  // series for the sparklines; the cards still work without it
  const detail = useAsync(() => loadRegionDetail(region.id), [region.id]);
  const d = detail.data?.region.id === region.id ? detail.data : undefined;
  return (
    <>
      <h2 className="panel__title">
        <Icon name="ranking" size={22} className="title-icon" />
        What changed across {region.phrase}?
      </h2>
      <p className="panel__period">
        {period.start} to {period.end}
      </p>
      <p className="panel__hint">Variables ranked by how clear their trend is. Pick one to see the details.</p>
      {error ? (
        <ErrorBox error={error} />
      ) : !data || data.region_id !== region.id ? (
        <Loading label="Loading ranking…" minHeight={300} />
      ) : (
        <ol className="ranking" key={region.id}>
          {data.ranking.map((r, i) => {
            const finding = r.significant && r.tier === 0;
            const series = d?.variables[r.variable]?.series;
            const years = series && d ? yearlyValues(d.dates, series.running_mean_12) : [];
            return (
              <li key={r.variable} style={{ '--i': i } as React.CSSProperties}>
                <button
                  type="button"
                  className={`rank-row ${finding ? '' : 'rank-row--muted'}`}
                  aria-current={r.variable === selectedVar ? 'true' : undefined}
                  onClick={() => onSelect(r.variable)}
                  style={{ '--var': varColor(r.variable) } as React.CSSProperties}
                >
                  <span className="rank-row__rank" aria-label={`Rank ${r.rank}`}>
                    {r.rank}
                  </span>
                  <span className="rank-row__body">
                    <span className="rank-row__name">
                      {varIcon(r.variable) && <Icon name={varIcon(r.variable)!} size={18} className="title-icon" />}
                      {r.name}
                    </span>
                    <span className="rank-row__meta">
                      <Direction r={r} />
                      <StatusBadge r={r} />
                    </span>
                    {r.slope_per_decade !== null && r.ci_per_decade && (
                      <span className="rank-row__value">
                        <strong>
                          {fmtSigned(r.slope_per_decade)} {r.public_unit}
                        </strong>{' '}
                        per decade (95% CI {fmtSigned(r.ci_per_decade[0])} to {fmtSigned(r.ci_per_decade[1])})
                      </span>
                    )}
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
