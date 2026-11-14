import { useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { loadCatalog, loadGrid, loadMeta, loadRegions, loadScreening, type Grid } from '../dataClient';
import { useAsync } from '../useAsync';
import { ErrorBox, Loading } from '../components/Status';
import { TrendMap } from '../components/TrendMap';
import { MapLegend } from '../components/MapLegend';
import { RankingPanel } from '../components/RankingPanel';
import { DetailView } from '../components/DetailView';
import { AsciiGlobe } from '../hero/AsciiGlobe';
import { Icon } from '../components/Icon';
import { varColor, varIcon } from '../viz';
import { PALETTE, gridToGeoJson, symmetricMax } from '../mapScale';

// grids are cached by dataClient, so their GeoJSON can be cached by identity too: switching back costs nothing
const geoCache = new WeakMap<Grid, ReturnType<typeof gridToGeoJson>>();
const cachedGeo = (g: Grid, max: number) => {
  if (!geoCache.has(g)) geoCache.set(g, gridToGeoJson(g, max, PALETTE));
  return geoCache.get(g)!;
};

export default function Explore() {
  const base = useAsync(() => Promise.all([loadMeta(), loadRegions(), loadCatalog(), loadScreening('global')]), []);
  const [params, setParams] = useSearchParams();
  const [globe, setGlobe] = useState(false);

  const [meta, regionList, catalog, globalRanking] = base.data ?? [];
  const variables = useMemo(
    () => (catalog && meta ? catalog.filter((v) => meta.variables_included.includes(v.id)) : []),
    [catalog, meta],
  );
  const regions = regionList?.regions ?? [];
  const regionId = regions.some((r) => r.id === params.get('region')) ? params.get('region')! : 'global';
  // default: the variable with the clearest global trend (same as "Surprise me")
  const top = globalRanking?.ranking.find((r) => variables.some((v) => v.id === r.variable));
  const defaultVar = top?.variable ?? variables[0]?.id ?? '';
  const varId = variables.some((v) => v.id === params.get('var')) ? params.get('var')! : defaultVar;
  const variable = variables.find((v) => v.id === varId);
  const region = regions.find((r) => r.id === regionId);

  const grid = useAsync(() => (varId ? loadGrid(varId) : Promise.resolve(undefined)), [varId]);
  const max = useMemo(() => (grid.data ? symmetricMax(grid.data.slope) : 1), [grid.data]);
  const geo = useMemo(() => (grid.data ? cachedGeo(grid.data, max) : undefined), [grid.data, max]);
  const gridMatches = grid.data?.variable === varId;

  const set = (values: { region?: string; var?: string }) =>
    setParams((p) => {
      for (const [k, v] of Object.entries(values)) if (v) p.set(k, v);
      return p;
    });
  const open = (values: { region?: string; var?: string }) => {
    set(values);
    document.getElementById('detail')?.scrollIntoView({ block: 'start' });
  };
  const toMap = () => {
    document.getElementById('map')?.scrollIntoView({ block: 'start' });
    document.getElementById('f-var')?.focus({ preventScroll: true });
  };

  if (base.error) return <ErrorBox error={base.error} />;
  if (!meta || !variable || !region) return <Loading label="Loading data…" minHeight={480} />;

  return (
    <>
      <header className="hero">
        <div>
          <h1>
            What changed on Earth from {meta.period.start.slice(0, 4)} to {meta.period.end.slice(0, 4)}?
          </h1>
          <p className="hero__lede">
            Pick a region on the map or from the list. EcoDelta shows which variables changed there, by how much, and
            whether the change is statistically significant.
          </p>
          <div className="hero__actions">
            <button type="button" className="btn" onClick={toMap}>
              Explore the map <Icon name="arrow-right" />
            </button>
            <Link className="btn btn--secondary" to="/guided">
              Guided questions <Icon name="arrow-right" />
            </Link>
          </div>
        </div>
        <AsciiGlobe />
      </header>
      <div className="explore">
        <section id="map" className="explore__map" aria-label="Trend map">
          <div className="controls">
            <div className="field" style={{ '--var': varColor(varId) } as React.CSSProperties}>
              <label className="field__label" htmlFor="f-var">
                Variable
              </label>
              {/* options cannot hold an SVG, so the selected variable's icon sits inside the closed select */}
              <div className={varIcon(varId) ? 'field__control field__control--icon' : 'field__control'}>
                {varIcon(varId) && <Icon name={varIcon(varId)!} className="field__icon" />}
                <select id="f-var" value={varId} onChange={(e) => set({ var: e.target.value })}>
                  {variables.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="field">
              <label className="field__label" htmlFor="f-region">
                Region
              </label>
              <select id="f-region" value={regionId} onChange={(e) => set({ region: e.target.value })}>
                {regions.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name}
                  </option>
                ))}
              </select>
            </div>
            <button
              type="button"
              className="btn btn--secondary btn--small"
              aria-pressed={globe}
              onClick={() => setGlobe((g) => !g)}
            >
              <Icon name="globe" />
              Globe view
            </button>
          </div>
          {grid.error ? (
            <ErrorBox error={grid.error} minHeight={420} />
          ) : (
            <TrendMap
              grid={gridMatches ? grid.data : undefined}
              geo={gridMatches ? geo : undefined}
              unit={variable.public_unit}
              regions={regions}
              selectedRegion={regionId}
              onSelectRegion={(id) => set({ region: id })}
              globe={globe}
              busy={grid.loading || !gridMatches}
              label={`Map of the trend in ${variable.name.toLowerCase()} per decade, ${meta.period.start} to ${meta.period.end}. Use the region list to choose a region with the keyboard.`}
            />
          )}
          <MapLegend palette={PALETTE} max={max} unit={variable.public_unit} period={meta.period} />
          <p className="note">{regionList!.note}</p>
        </section>
        <aside className="explore__panel" aria-label="Ranking for the selected region">
          <RankingPanel
            region={region}
            period={meta.period}
            selectedVar={varId}
            onSelect={(id) => open({ var: id })}
          />
        </aside>
        <section id="detail" className="explore__detail">
          <DetailView region={region} variable={variable} meta={meta} />
        </section>
      </div>
    </>
  );
}
