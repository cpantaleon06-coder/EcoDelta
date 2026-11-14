import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { loadCatalog, loadMeta, loadRegionDetail, loadRegions, loadScreening } from '../dataClient';
import { useAsync } from '../useAsync';
import { badgeFor, fmtP, fmtPercent, fmtSigned } from '../format';
import { varColor } from '../viz';
import { Panel } from '../components/ui';
import { ErrorBox, Loading } from '../components/Status';
import { TrendChart } from '../components/TrendChart';
import { TotalChangeBar } from '../components/TotalChangeBar';

const STEPS = ['What?', 'Where?', 'How much?', 'Can we trust it?'];

export default function Guided() {
  const base = useAsync(() => Promise.all([loadMeta(), loadRegions(), loadCatalog()]), []);
  const [step, setStep] = useState(0);
  const [varId, setVarId] = useState<string | null>(null);
  const [regionId, setRegionId] = useState('global');
  const [surprise, setSurprise] = useState<{ busy?: boolean; error?: Error; picked?: boolean }>({});
  const heading = useRef<HTMLHeadingElement>(null);
  const firstRender = useRef(true);
  const detail = useAsync(() => (step >= 2 ? loadRegionDetail(regionId) : Promise.resolve(undefined)), [step >= 2, regionId]);

  // move focus to the new question so keyboard and screen reader users follow the step change
  useEffect(() => {
    if (firstRender.current) firstRender.current = false;
    else heading.current?.focus();
  }, [step]);

  if (base.error) return <ErrorBox error={base.error} />;
  if (!base.data) return <Loading minHeight={420} />;
  const [meta, { regions, note }, catalog] = base.data;
  const variables = catalog.filter((v) => meta.variables_included.includes(v.id));
  const variable = variables.find((v) => v.id === varId);
  const region = regions.find((r) => r.id === regionId)!;

  const surpriseMe = () => {
    setSurprise({ busy: true });
    loadScreening('global').then(
      (s) => {
        setVarId(s.ranking[0].variable);
        setRegionId('global');
        setSurprise({ picked: true });
        setStep(1);
      },
      (error: Error) => setSurprise({ error }),
    );
  };

  const canNext = step === 0 ? !!variable : step < 3;
  const v = detail.data?.region.id === regionId && variable ? detail.data.variables[variable.id] : undefined;
  const period = `${meta.period.start} to ${meta.period.end}`;

  let body;
  if (step === 0) {
    body = (
      <fieldset className="choices">
        <legend className="sr-only">Choose a variable</legend>
        {variables.map((x) => (
          <label key={x.id} className="choice" style={{ '--var': varColor(x.id) } as React.CSSProperties}>
            <input type="radio" name="var" value={x.id} checked={varId === x.id} onChange={() => { setVarId(x.id); setSurprise({}); }} />
            <span className="choice__name">{x.name}</span>
            <span className="choice__text">{x.definition}</span>
          </label>
        ))}
        <div className="surprise">
          <button type="button" className="btn btn--secondary" onClick={surpriseMe} disabled={surprise.busy}>
            {surprise.busy ? 'Picking…' : 'Surprise me'}
          </button>
          <span className="muted">Picks the variable with the clearest trend for the whole globe.</span>
          {surprise.error && <ErrorBox error={surprise.error} />}
        </div>
      </fieldset>
    );
  } else if (step === 1) {
    body = (
      <>
        {surprise.picked && variable && (
          <p className="callout">
            Surprise pick: <strong>{variable.name}</strong> has the clearest trend for the whole globe.
          </p>
        )}
        <fieldset className="choices choices--regions">
          <legend className="sr-only">Choose a region</legend>
          {regions.map((r) => (
            <label key={r.id} className="choice choice--small">
              <input type="radio" name="region" value={r.id} checked={regionId === r.id} onChange={() => setRegionId(r.id)} />
              <span className="choice__name">{r.name}</span>
            </label>
          ))}
        </fieldset>
        <p className="note">{note}</p>
      </>
    );
  } else if (detail.error) {
    body = <ErrorBox error={detail.error} minHeight={300} />;
  } else if (!v || !variable) {
    body = <Loading minHeight={300} />;
  } else if (step === 2) {
    const hm = v.answers.how_much;
    const color = varColor(variable.id);
    body =
      hm.slope_per_decade === null || !hm.ci_per_decade ? (
        <>
          <p className="big-answer">No estimate</p>
          <p className="lede">{v.sentence}</p>
        </>
      ) : (
        <>
          <p className="big-answer">
            {fmtSigned(hm.slope_per_decade)} <span className="big-answer__unit">{variable.public_unit} per decade</span>
          </p>
          <p className="muted">
            95% CI {fmtSigned(hm.ci_per_decade[0])} to {fmtSigned(hm.ci_per_decade[1])}, {period}
          </p>
          {hm.total_change !== null && hm.total_change_ci && (
            <TotalChangeBar value={hm.total_change} ci={hm.total_change_ci} unit={variable.public_unit} years={hm.period_years} color={color} />
          )}
          {v.series && (
            <TrendChart
              dates={detail.data!.dates}
              series={v.series}
              slopePerDecade={v.report?.slope_per_decade ?? null}
              ciPerDecade={v.report ? [v.report.ci_low_per_decade, v.report.ci_high_per_decade] : null}
              significant={v.score.significant}
              unit={variable.public_unit}
              color={color}
              label={`Line chart of monthly ${variable.name.toLowerCase()} anomalies in ${region.phrase}, ${period}.`}
            />
          )}
          <p className="lede">{v.sentence}</p>
        </>
      );
  } else {
    const sig = v.answers.significance;
    const badge = badgeFor(v.score);
    body = (
      <>
        <p className="big-answer">
          <span className={`badge badge--lg ${badge.cls}`}>{badge.text}</span>
        </p>
        <p className="lede">{sig.explanation}</p>
        {sig.significant && <p>Significant does not mean large or important, and it says nothing about the cause.</p>}
        {v.cautions.length > 0 && (
          <ul className="cautions">
            {v.cautions.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        )}
        {v.score.tier !== 2 && (
        <p className="experts">
          For experts: p {fmtP(sig.pvalue)}
          {sig.test ? ` (${sig.test})` : ''}; q-value: not applicable, because this is one test for one region and
          variable (q-values are used on the map, where {fmtPercent(sig.cells_significant_after_fdr_fraction)} of this
          region's cells are significant after FDR).
        </p>
        )}
        <div className="wizard__end">
          <Link className="btn" to={`/explore?region=${region.id}&var=${variable.id}`}>
            See it on the map
          </Link>
          <button
            type="button"
            className="btn btn--secondary"
            onClick={() => {
              setStep(0);
              setVarId(null);
              setRegionId('global');
              setSurprise({});
            }}
          >
            Ask another question
          </button>
        </div>
      </>
    );
  }

  const titles = [
    'What do you want to look at?',
    variable ? `Where do you want to look at ${variable.name.toLowerCase()}?` : 'Where?',
    `How much did it change across ${region.phrase}?`,
    'Can we trust it?',
  ];

  return (
    <section className="page wizard">
      <h1>
        Guided questions
      </h1>
      <p className="lede">Four questions, one at a time: what changed, where, how much, and whether we can trust it.</p>
      <ol className="stepper">
        {STEPS.map((s, i) => (
          <li key={s} aria-current={i === step ? 'step' : undefined} className={i < step ? 'done' : ''}>
            <span className="stepper__n" aria-hidden="true">
              {i + 1}
            </span>
            {s}
            {i < step && <span className="sr-only"> (done)</span>}
          </li>
        ))}
      </ol>
      <Panel
        as="div"
        className="wizard__card"
        style={{ '--var': variable ? varColor(variable.id) : undefined } as React.CSSProperties}
      >
        <p className="eyebrow">
          Question {step + 1} of 4{step >= 1 && variable ? ` · ${variable.name}` : ''}
          {step >= 2 ? ` · ${region.name}` : ''}
        </p>
        <h2 ref={heading} tabIndex={-1}>
          {titles[step]}
        </h2>
        <div className="step-body" key={step}>
          {body}
        </div>
        <div className="wizard__nav">
          <button type="button" className="btn btn--secondary" onClick={() => setStep((s) => s - 1)} disabled={step === 0}>
            Back
          </button>
          {step < 3 && (
            <button type="button" className="btn" onClick={() => setStep((s) => s + 1)} disabled={!canNext}>
              Next
            </button>
          )}
        </div>
      </Panel>
    </section>
  );
}
