import { useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { loadCatalog, loadGrid, loadMeta, loadRegions, type Grid } from '../dataClient';
import { applyAction, mapView, readSelection, type Action } from '../mapState';
import { useAsync } from '../useAsync';
import { ErrorBox, Loading } from '../components/Status';
import { TrendMap } from '../components/TrendMap';
import { MapLegend } from '../components/MapLegend';
import { RankingPanel } from '../components/RankingPanel';
import { DetailView } from '../components/DetailView';
import { Profile } from '../components/Profile';
import { AsciiGlobe } from '../hero/AsciiGlobe';
import { Icon } from '../components/Icon';
import { varIcon } from '../viz';
import { MAP_CORRELATION_NOTE } from '../copy';
import { fmtPercent } from '../format';
import { PALETTE, gridToGeoJson, symmetricMax } from '../mapScale';

// grids are cached by dataClient, so their GeoJSON can be cached by identity too: switching back costs nothing
const geoCache = new WeakMap<Grid, ReturnType<typeof gridToGeoJson>>();
const cachedGeo = (g: Grid, max: number) => {
  if (!geoCache.has(g)) geoCache.set(g, gridToGeoJson(g, max, PALETTE));
  return geoCache.get(g)!;
};

export default function Explore() {
  const base = useAsync(() => Promise.all([loadMeta(), loadRegions(), loadCatalog()]), []);
  const [params, setParams] = useSearchParams();
  const [globe, setGlobe] = useState(false);

  const [meta, regionList, catalog] = base.data ?? [];
  const variables = useMemo(
    () => (catalog && meta ? catalog.filter((v) => meta.variables_included.includes(v.id)) : []),
    [catalog, meta],
  );
  const regions = regionList?.regions ?? [];
  // no variable in the URL = overview: the plain world map, no data layer
  const selection = readSelection(params, variables.map((v) => v.id), regions.map((r) => r.id));
  const { variable: varId, region: regionId } = selection;
  const view = mapView(selection);
  const variable = variables.find((v) => v.id === varId);
  const region = regions.find((r) => r.id === regionId);

  const grid = useAsync(() => (varId ? loadGrid(varId) : Promise.resolve(undefined)), [varId]);
  const max = useMemo(() => (grid.data ? symmetricMax(grid.data.slope) : 1), [grid.data]);
  const geo = useMemo(() => (grid.data ? cachedGeo(grid.data, max) : undefined), [grid.data, max]);
  const gridMatches = grid.data?.variable === varId;

  const act = (action: Action) => setParams((p) => applyAction(p, action));
  const open = (id: string) => {
    act({ type: 'variable', id });
    document.getElementById('detail')?.scrollIntoView({ block: 'start' });
  };
  const toMap = () => {
    document.getElementById('map')?.scrollIntoView({ block: 'start' });
    document.getElementById('f-var')?.focus({ preventScroll: true });
  };

  const fdr = meta?.methods.fdr as { q?: number } | undefined;
  const fdrQ = typeof fdr?.q === 'number' ? fdr.q : undefined;

  if (base.error) return <ErrorBox error={base.error} />;
  if (!meta || !region) return <Loading label="Loading data…" minHeight={480} />;

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
            <div className="field field--wide">
              <label className="field__label" htmlFor="f-var">
                Variable
              </label>
              {/* options cannot hold an SVG, so the selected variable's icon sits inside the closed select */}
              <div className={varId && varIcon(varId) ? 'field__control field__control--icon' : 'field__control'}>
                {varId && varIcon(varId) && <Icon name={varIcon(varId)!} className="field__icon" />}
                <select
                  id="f-var"
                  value={varId ?? ''}
                  onChange={(e) => act(e.target.value ? { type: 'variable', id: e.target.value } : { type: 'clear' })}
                >
                  {!varId && <option value="">Choose a variable</option>}
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
              <select id="f-region" value={regionId} onChange={(e) => act({ type: 'region', id: e.target.value })}>
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
              unit={variable?.public_unit ?? ''}
              regions={regions}
              selectedRegion={regionId}
              onSelectRegion={(id) => act({ type: 'region', id })}
              globe={globe}
              showData={view.showData}
              onClear={() => act({ type: 'clear' })}
              dimOthers={view.dimOthers}
              busy={!!varId && (grid.loading || !gridMatches)}
              label={
                variable
                  ? `Map of the trend in ${variable.name.toLowerCase()} per decade, ${meta.period.start} to ${meta.period.end}, over a world map. Use the variable and region lists to choose with the keyboard.`
                  : 'World map with coastlines and the approximate study areas outlined. Use the variable and region lists to choose with the keyboard.'
              }
            />
          )}
          {variable ? (
            <MapLegend
              palette={PALETTE}
              max={max}
              unit={variable.public_unit}
              period={meta.period}
              areaNote={view.highlight && region.kind === 'approximate_box' ? region.display_note : undefined}
            />
          ) : (
            <p className="map-caption">Pick a variable or a region to see how it changed.</p>
          )}
          <p className="note">{regionList!.note}</p>
          <p className="note">
            {MAP_CORRELATION_NOTE} {fdrQ !== undefined ? fmtPercent(fdrQ) : 'level'}.
          </p>
          <div className="fill" aria-hidden="true" />
        </section>
        <aside className="explore__panel" aria-label="Ranking for the selected region">
          <RankingPanel
            region={region}
            period={meta.period}
            variables={variables}
            selectedVar={varId ?? ''}
            onSelect={open}
          />
          <div className="fill" aria-hidden="true" />
        </aside>
        <div id="profile" className="explore__detail">
          <Profile region={region} variables={variables} />
        </div>
        <section id="detail" className="explore__detail">
          {variable ? (
            <DetailView region={region} variable={variable} meta={meta} />
          ) : (
            <p className="callout">Pick a variable in the list above the map or in the ranking to see the details for {region.phrase}.</p>
          )}
        </section>
      </div>
    </>
  );
}
