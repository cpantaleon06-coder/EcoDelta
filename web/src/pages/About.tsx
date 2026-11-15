import { isDemoData, loadCatalog, loadMeta, loadRegions } from '../dataClient';
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
          The decorative globe on the Explore page uses land outlines from Natural Earth 1:110m (public domain), via
          the world-atlas package (ISC). It shows no data.
        </p>
      </section>
    </article>
  );
}
