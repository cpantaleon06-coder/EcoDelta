import { useSearchParams } from 'react-router-dom';
import { loadCatalog, loadCompare, loadMeta, loadRegionDetail, loadRegions, type Region, type RegionTrend } from '../dataClient';
import { useAsync } from '../useAsync';
import { fmtP, fmtPercent, fmtSigned } from '../format';
import { varColor, varIcon } from '../viz';
import { findPair } from '../results';
import { ErrorBox, Loading } from '../components/Status';
import { Icon } from '../components/Icon';
import { CompareChart } from '../components/CompareChart';
import { TrendChart } from '../components/TrendChart';
import { AreaTag, Evidence, SourceLine } from '../components/ResultMeta';

// required caveats (audit 5), shown with every comparison
const CAVEATS = [
  'A trend that is significant in one region and not in the other does not show that the two trends differ.',
  'Looking at many pairs raises the chance of false positives.',
];

// D(t) = A(t) - B(t), month by month: a plain subtraction of the exported series, no statistics in the browser
const minus = (x: (number | null)[], y: (number | null)[]) => x.map((v, i) => (v === null || y[i] === null ? null : v - y[i]!));

const ci = (c: [number, number] | null) => (c ? `95% CI ${fmtSigned(c[0])} to ${fmtSigned(c[1])}` : '95% CI not available');

function TrendCard({ region, t, unit }: { region: Region; t: RegionTrend; unit: string }) {
  return (
    <div className="answer">
      <h3>
        {region.name} <AreaTag region={region} />
      </h3>
      {t.slope_per_decade === null ? (
        <p className="answer__big">No estimate</p>
      ) : (
        <p className="answer__big">
          {fmtSigned(t.slope_per_decade)} <span className="answer__unit">{unit} per decade</span>
        </p>
      )}
      <p>{ci(t.ci_per_decade)}</p>
      <p>
        <Evidence cls={t.evidence_class ?? undefined} />
      </p>
      <p className="experts">For experts: p {fmtP(t.pvalue)} (this region alone)</p>
    </div>
  );
}

export default function Compare() {
  const base = useAsync(() => Promise.all([loadMeta(), loadRegions(), loadCatalog()]), []);
  const [params, setParams] = useSearchParams();
  const [meta, regionList, catalog] = base.data ?? [];
  const variables = catalog && meta ? catalog.filter((v) => meta.variables_included.includes(v.id)) : [];
  const regions = regionList?.regions ?? [];
  const pick = (key: string, ok: string[], fallback: string) => (ok.includes(params.get(key) ?? '') ? params.get(key)! : fallback);
  const varId = pick('var', variables.map((v) => v.id), variables[0]?.id ?? '');
  const ids = regions.map((r) => r.id);
  const aId = pick('a', ids, ids[0] ?? '');
  const bId = pick('b', ids, ids[1] ?? '');
  const variable = variables.find((v) => v.id === varId);
  const set = (k: string, v: string) =>
    setParams((p) => {
      p.set(k, v);
      return p;
    });

  const file = useAsync(() => (varId ? loadCompare(varId) : Promise.resolve(undefined)), [varId]);
  const series = useAsync(
    () => (aId && bId && aId !== bId ? Promise.all([loadRegionDetail(aId), loadRegionDetail(bId)]) : Promise.resolve(undefined)),
    [aId, bId],
  );

  if (base.error) return <ErrorBox error={base.error} />;
  if (!meta || !variable) return <Loading label="Loading data…" minHeight={480} />;

  const pair = file.data?.variable === varId && aId !== bId ? findPair(file.data, aId, bId) : undefined;
  // the pair keeps the file's order: the difference is always region_a minus region_b
  const ra = regions.find((r) => r.id === pair?.region_a);
  const rb = regions.find((r) => r.id === pair?.region_b);
  const unit = file.data?.public_unit ?? variable.public_unit;
  const color = varColor(varId);
  // by id, so a stale load for the previous pair never shows under the new names
  const sa = series.data?.find((d) => d.region.id === ra?.id);
  const sb = series.data?.find((d) => d.region.id === rb?.id);
  const seriesA = sa?.variables[varId]?.series;
  const seriesB = sb?.variables[varId]?.series;

  const select = (id: string, label: string, value: string, key: string, options: { id: string; name: string }[], wide = false) => (
    <div className={wide ? 'field field--wide' : 'field'}>
      <label className="field__label" htmlFor={id}>
        {label}
      </label>
      <select id={id} value={value} onChange={(e) => set(key, e.target.value)}>
        {options.map((o) => (
          <option key={o.id} value={o.id}>
            {o.name}
          </option>
        ))}
      </select>
    </div>
  );

  return (
    <article className="page compare" style={{ '--var': color } as React.CSSProperties}>
      <h1>Compare two regions</h1>
      <p className="lede">
        Did a variable change differently in two regions? The test looks at the difference between the two regional series
        month by month, and asks whether that difference has a trend.
      </p>
      <div className="controls">
        {select('c-var', 'Variable', varId, 'var', variables, true)}
        {select('c-a', 'Region A', aId, 'a', regions)}
        {select('c-b', 'Region B', bId, 'b', regions)}
      </div>

      {aId === bId ? (
        <p className="callout">Choose two different regions.</p>
      ) : file.error ? (
        <ErrorBox error={file.error} />
      ) : !file.data || file.data.variable !== varId ? (
        <Loading label="Loading comparison…" minHeight={360} />
      ) : !pair || !ra || !rb ? (
        <p className="callout">This pair is not available in the data.</p>
      ) : (
        <>
          <section className="verdict" aria-labelledby="verdict-title">
            <p className="eyebrow">
              {varIcon(varId) && <Icon name={varIcon(varId)!} size={16} className="title-icon" />}
              {variable.name} · {file.data.period[0]} to {file.data.period[1]}
            </p>
            <div className="verdict__head">
              <h2 id="verdict-title" className={pair.independent ? undefined : 'verdict--soft'}>
                Verdict: {pair.verdict}
              </h2>
              {!pair.independent && (
                <span className="badge badge--lg badge--caution">
                  <Icon name="info" size={16} /> Overlapping regions, interpret with caution
                </span>
              )}
            </div>
            <SourceLine provenance={variable.provenance} />
            {!pair.independent && (
              <p className="callout callout--warn">
                <strong>Overlapping study areas.</strong> {fmtPercent(pair.overlap_fraction)} of the smaller box lies inside
                the other one. These two regions overlap, so their averages share data and the two results are not
                independent. The test is applied to the difference between the two averages. Shared cells do not fully
                cancel, because each average is divided by its own area, so read this as a comparison of two overlapping
                areas.
              </p>
            )}
          </section>

          <section className="answers" aria-label="Trends and their difference">
            <TrendCard region={ra} t={pair.trend_a} unit={unit} />
            <TrendCard region={rb} t={pair.trend_b} unit={unit} />
            <div className="answer answer--num">
              <h3>
                Trend of the difference ({ra.name} minus {rb.name})
              </h3>
              {pair.difference_slope_per_decade === null ? (
                <p className="answer__big">No estimate</p>
              ) : (
                <p className="answer__big">
                  {fmtSigned(pair.difference_slope_per_decade)} <span className="answer__unit">{unit} per decade</span>
                </p>
              )}
              <p>
                {ci(pair.difference_ci_per_decade)}; p {fmtP(pair.pvalue)}; {pair.n_common_months} months with data in
                both regions.
              </p>
              <p className="experts">
                For experts: q across all pairs of this variable {pair.q_across_pairs === null ? 'not available' : `= ${pair.q_across_pairs}`}.{' '}
                {file.data.q_note}
              </p>
            </div>
          </section>

          <ul className="cautions compare__caveats">
            {CAVEATS.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>

          {series.error ? (
            <ErrorBox error={series.error} />
          ) : !sa || !seriesA || !seriesB ? (
            <Loading label="Loading series…" minHeight={300} />
          ) : (
            <>
              <CompareChart
                dates={sa.dates}
                a={{ name: ra.name, values: seriesA.running_mean_12 }}
                b={{ name: rb.name, values: seriesB.running_mean_12 }}
                unit={unit}
                color={color}
                label={`Line chart of the 12-month running mean of ${variable.name.toLowerCase()} anomalies in ${ra.name} and ${rb.name}.`}
              />
              <h3 className="compare__diff-title">
                Difference series: {ra.name} minus {rb.name}
              </h3>
              <TrendChart
                dates={sa.dates}
                series={{ anomaly: minus(seriesA.anomaly, seriesB.anomaly), running_mean_12: minus(seriesA.running_mean_12, seriesB.running_mean_12) }}
                slopePerDecade={pair.difference_slope_per_decade}
                ciPerDecade={pair.difference_ci_per_decade}
                significant={pair.verdict === 'trends differ'}
                unit={unit}
                color={color}
                names={{ a: 'Monthly difference (the series the test uses)', m: 'Difference of the two 12-month running means' }}
                label={`Line chart of the monthly difference in ${variable.name.toLowerCase()} anomalies, ${ra.name} minus ${rb.name}, with the trend of the difference.`}
              />
              <p className="note">
                The difference is computed in your browser by subtracting the two exported monthly series. The slope, its
                95% CI and the verdict come from the data files.
              </p>
            </>
          )}

          <details className="how">
            <summary>How was this computed?</summary>
            <p>{file.data.method}</p>
            <p>{file.data.note}</p>
          </details>
        </>
      )}
    </article>
  );
}
