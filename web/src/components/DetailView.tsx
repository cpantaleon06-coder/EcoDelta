import { loadRegionDetail, type Meta, type Region, type Variable, type Verdict } from '../dataClient';
import { useAsync } from '../useAsync';
import { badgeFor, fmt, fmtP, fmtPercent, fmtSigned } from '../format';
import { PALETTE } from '../mapScale';
import { varColor, yearlyValues, varIcon } from '../viz';
import { Stripes } from './ui';
import { ErrorBox, Loading } from './Status';
import { TrendChart } from './TrendChart';
import { MethodsList } from './MethodsList';
import { Icon } from './Icon';
import { StatusBadge } from './StatusBadge';

const VERDICT_TEXT: Record<Verdict, string> = {
  increasing: 'It went up',
  decreasing: 'It went down',
  'no significant trend': 'No clear trend',
  'insufficient data': 'Not enough data to tell',
};

interface Props {
  region: Region;
  variable: Variable;
  meta: Meta;
}

export function DetailView({ region, variable, meta }: Props) {
  const { data, error } = useAsync(() => loadRegionDetail(region.id), [region.id]);
  if (error) return <ErrorBox error={error} minHeight={400} />;
  if (!data || data.region.id !== region.id) return <Loading label="Loading details…" minHeight={400} />;
  const v = data.variables[variable.id];
  if (!v) return <ErrorBox error={new Error(`No results for ${variable.name} in ${region.phrase}.`)} />;

  const { what, where, how_much, significance } = v.answers;
  const unit = variable.public_unit;
  const badge = badgeFor({ tier: v.score.tier, significant: v.score.significant });
  const warnings = [...new Set([...(v.report?.warnings ?? []), ...significance.warnings])];
  const color = varColor(variable.id);
  const years = v.series ? yearlyValues(data.dates, v.series.running_mean_12) : [];

  return (
    <article key={`${region.id}-${variable.id}`} className="detail" aria-labelledby="detail-title" style={{ '--var': color } as React.CSSProperties}>
      <header className="detail__head">
        {years.length > 1 && (
          <figure className="detail__stripes">
            <Stripes years={years} palette={PALETTE} />
            <figcaption>
              <span>{years[0].year}</span>
              <span>One stripe per year: the 12-month running mean in December</span>
              <span>{years[years.length - 1].year}</span>
            </figcaption>
          </figure>
        )}
        <p className="eyebrow">
          Rank {v.rank} in {region.name} · {meta.period.start} to {meta.period.end}
        </p>
        <h2 id="detail-title">
          {varIcon(variable.id) && <Icon name={varIcon(variable.id)!} size={28} className="title-icon" />}
          {variable.name} across {region.phrase} <StatusBadge r={v.score} />
        </h2>
        <p className="detail__sentence">{v.sentence}</p>
        {v.cautions.length > 0 && (
          <ul className="cautions">
            {v.cautions.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        )}
      </header>

      {v.series ? (
        <TrendChart
          dates={data.dates}
          series={v.series}
          slopePerDecade={v.report?.slope_per_decade ?? null}
          ciPerDecade={v.report ? [v.report.ci_low_per_decade, v.report.ci_high_per_decade] : null}
          significant={v.score.significant}
          unit={unit}
          color={color}
          label={`Line chart of monthly ${variable.name.toLowerCase()} anomalies in ${region.phrase}, ${meta.period.start} to ${meta.period.end}. ${v.sentence}`}
        />
      ) : (
        <p className="empty">There is no time series for this variable in this region.</p>
      )}

      <section aria-label="Four questions" className="answers">
        <div className="answer">
          <h3>
            <Icon name="q-what" size={16} /> What changed?
          </h3>
          <p className="answer__big">{VERDICT_TEXT[what.verdict]}</p>
          <p>{what.name}</p>
        </div>
        <div className="answer">
          <h3>
            <Icon name="q-where" size={16} /> Where?
          </h3>
          <p className="answer__big">{where.name}</p>
          <p>
            {where.n_valid_cells} of {where.n_box_cells} grid cells have enough data ({fmtPercent(where.covered_fraction)}{' '}
            of the box area){where.land_only ? ', land only' : ''}. The box is outlined on the map.
          </p>
        </div>
        <div className="answer answer--num">
          <h3>
            <Icon name="q-how-much" size={16} /> How much?
          </h3>
          {how_much.slope_per_decade === null || !how_much.ci_per_decade ? (
            <p className="answer__big">No estimate</p>
          ) : (
            <>
              <p className="answer__big">
                {fmtSigned(how_much.slope_per_decade)} <span className="answer__unit">{unit} per decade</span>
              </p>
              <p>
                95% CI {fmtSigned(how_much.ci_per_decade[0])} to {fmtSigned(how_much.ci_per_decade[1])}.
                {how_much.total_change !== null && how_much.total_change_ci && (
                  <>
                    {' '}
                    Over {fmt(how_much.period_years)} years: {fmtSigned(how_much.total_change)} {unit} (95% CI{' '}
                    {fmtSigned(how_much.total_change_ci[0])} to {fmtSigned(how_much.total_change_ci[1])}).
                  </>
                )}
              </p>
            </>
          )}
        </div>
        <div className="answer">
          <h3>
            <Icon name="q-trust" size={16} /> Is it significant?
          </h3>
          <p className="answer__big">{badge.text}</p>
          <p>{significance.explanation}</p>
          <p className="experts">
            For experts: p {fmtP(significance.pvalue)}
            {significance.test ? ` (${significance.test})` : ''}; grid cells significant after FDR:{' '}
            {fmtPercent(significance.cells_significant_after_fdr_fraction)}; q-value: not applicable (one test per region
            and variable).
          </p>
        </div>
      </section>

      <section className="about-var">
        <h3>
          <Icon name="info" size={18} className="title-icon" />
          About this variable
        </h3>
        <div>
          <p>{variable.definition}</p>
          <p>{variable.increase_means}</p>
        </div>
        <div>
          <ul>
            {variable.caveats.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
          {warnings.length > 0 && (
            <>
              <h4>Technical warnings for this result</h4>
              <ul className="cautions">
                {warnings.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            </>
          )}
        </div>
      </section>

      <details className="how">
        <summary>How was this computed?</summary>
        <MethodsList methods={meta.methods} />
        <h4>Limitations</h4>
        <ul>
          {meta.limitations.map((l) => (
            <li key={l}>{l}</li>
          ))}
        </ul>
      </details>
    </article>
  );
}
