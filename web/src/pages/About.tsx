import { isDemoData, loadCatalog, loadMeta, loadRegions, type Provenance } from '../dataClient';
import { describeValue, humanizeKey } from '../format';
import { NA } from '../results';
import { useAsync } from '../useAsync';
import { ErrorBox, Loading } from '../components/Status';
import { MethodsList } from '../components/MethodsList';
import { EXPLAINERS } from '../copy';
import { Icon } from '../components/Icon';
import { varIcon } from '../viz';

// Show DOIs exactly as exported; link only values that look like a DOI.
const Doi = ({ doi }: { doi: string }) =>
  /^10\.\d{4,9}\/\S+$/.test(doi) ? (
    <a href={`https://doi.org/${doi}`} className="ext">
      {doi}
      <Icon name="external" size={14} />
      <span className="sr-only"> (doi.org)</span>
    </a>
  ) : (
    <>{doi}</>
  );

// every provenance field, in reading order; values are shown as exported, nulls as "not available"
const PROVENANCE: [string, (p: Provenance) => React.ReactNode][] = [
  ['Product', (p) => p.product_short_name],
  ['Collection', (p) => p.collection_id],
  ['Version', (p) => p.version],
  ['DOI', (p) => p.doi && <Doi doi={p.doi} />],
  ['Source variable', (p) => p.source_variable],
  ['Source units', (p) => p.source_units],
  ['Units', (p) => p.units],
  ['Displayed units', (p) => p.displayed_units],
  ['Native resolution', (p) => p.native_resolution && describeValue(p.native_resolution)],
  ['Grid', (p) => describeValue(p.grid)],
  ['Temporal resolution', (p) => p.temporal_resolution && describeValue(p.temporal_resolution)],
  ['Period', (p) => p.period && `${p.period[0]} to ${p.period[1]}`],
  ['Retrieved', (p) => p.retrieved && describeValue(p.retrieved)],
  [
    'Processing',
    (p) =>
      p.processing_steps && (
        <ol>
          {p.processing_steps.map((s) => (
            <li key={s.step}>
              {s.step}: {s.detail}
            </li>
          ))}
        </ol>
      ),
  ],
  [
    'Statistical method',
    (p) =>
      p.statistics && (
        <ul>
          {Object.entries(p.statistics).map(([k, v]) => (
            <li key={k}>
              {humanizeKey(k)}: {describeValue(v)}
            </li>
          ))}
        </ul>
      ),
  ],
  [
    'Engine commit',
    (p) =>
      p.engine_commit && (
        <>
          <code className="hash">{p.engine_commit}</code>
          {p.engine_uncommitted_changes ? ' (with uncommitted changes)' : ''}
        </>
      ),
  ],
  ['Manifest hash (SHA-256)', (p) => p.manifest_sha256 && <code className="hash">{p.manifest_sha256}</code>],
];

const version = (x: { version: string; commit: string | null; uncommitted_changes: boolean }) =>
  `${x.version}${x.commit ? `, commit ${x.commit.slice(0, 7)}` : ''}${x.uncommitted_changes ? ' (with uncommitted changes)' : ''}`;

export default function About() {
  const { data, error } = useAsync(() => Promise.all([loadMeta(), loadCatalog(), loadRegions()]), []);
  if (error) return <ErrorBox error={error} />;
  if (!data) return <Loading minHeight={420} />;
  const [meta, catalog, { regions, note }] = data;

  return (
    <article className="page about">
      <h1>
        About the data
      </h1>
      <p className="lede">
        EcoDelta shows trends from {meta.period.start} to {meta.period.end} ({meta.period.n_months} months, about{' '}
        {meta.period.years} years) on a {meta.grid.resolution_deg}-degree grid and in {regions.length} regions. All numbers
        were computed in advance; this website only displays them.
      </p>
      {isDemoData(meta) && (
        <p className="callout callout--warn">
          This build uses <strong>synthetic demo data</strong> (source: {meta.source}). The numbers are not real observations.
        </p>
      )}

      <section aria-labelledby="products">
        <h2 id="products">Data products</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th scope="col">Product</th>
                <th scope="col">Short name</th>
                <th scope="col">Version</th>
                <th scope="col">DOI</th>
                <th scope="col">Variables</th>
              </tr>
            </thead>
            <tbody>
              {meta.products.map((p) => (
                <tr key={`${p.short_name}-${p.version}`}>
                  <td>{p.name}</td>
                  <td>{p.short_name}</td>
                  <td>{p.version}</td>
                  <td>
                    <Doi doi={p.doi} />
                  </td>
                  <td>{p.variables.join(', ')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <h3>Citations</h3>
        <ul>
          {meta.products.map((p) => (
            <li key={`${p.short_name}-${p.version}`}>
              <strong>{p.short_name}:</strong> {p.citation}
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="variables">
        <h2 id="variables">Variables</h2>
        <dl className="vars">
          {catalog.map((v) => (
            <div key={v.id}>
              <dt>
                {varIcon(v.id) && <Icon name={varIcon(v.id)!} size={20} className="title-icon" />}
                {v.name} <span className="muted">({v.public_unit})</span>
                {!meta.variables_included.includes(v.id) && <span className="badge badge--none">Not in this build</span>}
              </dt>
              <dd>
                {v.definition} {v.land_only ? 'Land only.' : ''} Source: {v.product.short_name}, variable{' '}
                <code>{v.product.source_variable}</code>.
              </dd>
            </div>
          ))}
        </dl>
        {meta.variables_missing.length > 0 && <p className="note">Missing from this build: {meta.variables_missing.join(', ')}.</p>}
      </section>

      <section aria-labelledby="provenance">
        <h2 id="provenance">Data provenance</h2>
        <p>
          Where each variable comes from and how it was processed, as recorded by the engine. Engine commit:{' '}
          <code className="hash">{meta.engine.commit ?? NA}</code>. Manifest hash (SHA-256): <code className="hash">{meta.data?.manifest_sha256 ?? NA}</code>.
        </p>
        {catalog.map((v, i) => (
          <details key={v.id} className="prov" open={i === 0}>
            <summary>
              {varIcon(v.id) && <Icon name={varIcon(v.id)!} size={18} className="title-icon" />}
              {v.name}
            </summary>
            {v.provenance ? (
              <div className="table-wrap">
                <table>
                  <caption className="sr-only">Provenance of {v.name}</caption>
                  <tbody>
                    {PROVENANCE.map(([label, get]) => (
                      <tr key={label}>
                        <th scope="row">{label}</th>
                        <td>{get(v.provenance!) || NA}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="note">Provenance: {NA}.</p>
            )}
          </details>
        ))}
      </section>

      <section aria-labelledby="reading">
        <h2 id="reading">How to read the results</h2>
        <dl className="vars">
          {EXPLAINERS.map((e) => (
            <div key={e.term}>
              <dt>{e.term}</dt>
              <dd>{e.text}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section aria-labelledby="methods">
        <h2 id="methods">Methods</h2>
        <MethodsList methods={meta.methods} />
      </section>

      <section aria-labelledby="limits">
        <h2 id="limits">Limitations</h2>
        <ul>
          {meta.limitations.map((l) => (
            <li key={l}>{l}</li>
          ))}
          {!meta.limitations.includes(note) && <li>{note}</li>}
        </ul>
      </section>

      <section aria-labelledby="build">
        <h2 id="build">Build</h2>
        <p className="muted">
          Built {meta.build_date} · data format {meta.schema_version} · engine {version(meta.engine)} · trendkit{' '}
          {version(meta.trendkit)}
        </p>
        <p className="muted">
          Open-source licenses shipped with this site: <a href="licenses/maplibre-gl.txt">MapLibre GL JS (BSD-3-Clause)</a>,{' '}
          <a href="licenses/poppins-OFL.txt">Poppins (OFL-1.1)</a>.
        </p>
        <p className="muted">
          The land and coastlines of the map, and the decorative globe on the Explore page, use Natural Earth 1:50m land
          (public domain, made with Natural Earth), via the world-atlas package (ISC), simplified for the web. The map
          draws coastlines only, no country borders.
        </p>
      </section>
    </article>
  );
}
