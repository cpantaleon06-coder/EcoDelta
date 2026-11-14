import { useEffect, useRef, useState } from 'react';
import maplibregl, { type GeoJSONSource, type Map as MlMap, type StyleSpecification } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import type { Grid, Region } from '../dataClient';
import { boxBounds, cellCenter, cellIndexAt, graticule, regionAt, regionsToGeoJson } from '../mapScale';
import { reducedMotion } from '../viz';
import { fmt, fmtLatLon, fmtSigned } from '../format';

type Fc = GeoJSON.FeatureCollection;
const EMPTY: Fc = { type: 'FeatureCollection', features: [] };
// map ink (same values as --map-bg, --rule, --text-2 and --text in styles/tokens.css)
const INK = { bg: '#050d12', grid: '#1b2f3a', line: '#b3cbcc', text: '#e4f1ef', selected: '#e4f1ef' };
const WORLD: [[number, number], [number, number]] = [[-179, -62], [179, 80]];

// No basemap tiles: a plain background plus our own layers.
const STYLE: StyleSpecification = {
  version: 8,
  sources: {},
  layers: [{ id: 'bg', type: 'background', paint: { 'background-color': INK.bg } }],
};

interface Props {
  grid?: Grid;
  geo?: { cells: Fc; dots: Fc };
  unit: string;
  regions: Region[];
  selectedRegion: string;
  onSelectRegion: (id: string) => void;
  globe: boolean;
  busy: boolean;
  label: string;
}

interface Hover {
  x: number;
  y: number;
  w: number;
  h: number;
  index: number;
  region?: Region;
}

export function TrendMap({ grid, geo, unit, regions, selectedRegion, onSelectRegion, globe, busy, label }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MlMap | null>(null);
  const [ready, setReady] = useState(false);
  const [hover, setHover] = useState<Hover | null>(null);
  const [failed, setFailed] = useState(false);
  // event handlers are bound once; read current values through refs
  const live = useRef({ grid, regions, onSelectRegion });
  live.current = { grid, regions, onSelectRegion };

  useEffect(() => {
    let map: MlMap;
    try {
      map = new maplibregl.Map({
      container: container.current!,
      style: STYLE,
      bounds: WORLD,
      minZoom: 0,
      maxZoom: 6,
      attributionControl: false,
      dragRotate: false,
      pitchWithRotate: false,
      renderWorldCopies: false,
      });
    } catch {
      setFailed(true); // usually WebGL is off or unavailable
      return;
    }
    map.touchZoomRotate.disableRotation();
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
    mapRef.current = map;

    map.on('load', () => {
      map.addSource('graticule', { type: 'geojson', data: graticule(30) });
      map.addSource('cells', { type: 'geojson', data: EMPTY });
      map.addSource('dots', { type: 'geojson', data: EMPTY });
      map.addSource('regions', { type: 'geojson', data: EMPTY });
      map.addLayer({ id: 'graticule', type: 'line', source: 'graticule', paint: { 'line-color': INK.grid, 'line-width': 1 } });
      map.addLayer({
        id: 'cells',
        type: 'fill',
        source: 'cells',
        paint: { 'fill-color': ['get', 'c'], 'fill-opacity': ['case', ['==', ['get', 's'], 1], 1, 0.28], 'fill-antialias': false },
      });
      // soft glow under significant cells, in their own color
      map.addLayer({
        id: 'glow',
        type: 'circle',
        source: 'dots',
        paint: {
          'circle-color': ['get', 'c'],
          'circle-opacity': 0.22,
          'circle-blur': 1,
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 0, 2.5, 2, 5, 5, 14],
        },
      });
      map.addLayer({
        id: 'dots',
        type: 'circle',
        source: 'dots',
        paint: {
          'circle-color': INK.text,
          'circle-opacity': 0.6,
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 0, 0.6, 2, 1.1, 5, 2.4],
        },
      });
      map.addLayer({ id: 'regions', type: 'line', source: 'regions', paint: { 'line-color': INK.line, 'line-opacity': 0.4, 'line-width': 1, 'line-dasharray': [3, 2] } });
      map.addLayer({ id: 'region-selected', type: 'line', source: 'regions', filter: ['==', ['get', 'id'], ''], paint: { 'line-color': INK.selected, 'line-width': 2.5 } });

      // Optional coastline overlay; skipped silently when the file is missing or not GeoJSON.
      fetch(`${import.meta.env.BASE_URL}data/coastlines.geojson`)
        .then((r) => (r.ok ? r.json() : Promise.reject()))
        .then((data: Fc) => {
          if (data?.type !== 'FeatureCollection') return;
          map.addSource('coast', { type: 'geojson', data });
          map.addLayer({ id: 'coast', type: 'line', source: 'coast', paint: { 'line-color': INK.line, 'line-opacity': 0.55, 'line-width': 0.7 } }, 'regions');
        })
        .catch(() => {});
      setReady(true);
    });

    const pick = (e: maplibregl.MapMouseEvent) => {
      const g = live.current.grid;
      const { lng, lat } = e.lngLat;
      return {
        x: e.point.x,
        y: e.point.y,
        w: map.getCanvas().clientWidth,
        h: map.getCanvas().clientHeight,
        index: g ? cellIndexAt(lng, lat, g.lat, g.lon) : -1,
        region: regionAt(lng, lat, live.current.regions),
      };
    };
    map.on('mousemove', (e) => {
      const h = pick(e);
      map.getCanvas().style.cursor = h.region ? 'pointer' : '';
      setHover(h);
    });
    map.on('mouseout', () => setHover(null));
    map.on('click', (e) => {
      const h = pick(e);
      setHover(h); // on touch screens a tap shows the cell info
      if (h.region) live.current.onSelectRegion(h.region.id);
    });
    return () => map.remove();
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    (map.getSource('cells') as GeoJSONSource).setData(geo?.cells ?? EMPTY);
    (map.getSource('dots') as GeoJSONSource).setData(geo?.dots ?? EMPTY);
    // short fade-in when the variable changes (compositor-only, so it cannot stall the main thread)
    if (geo && !reducedMotion()) map.getCanvas().animate?.([{ opacity: 0.35 }, { opacity: 1 }], { duration: 260, easing: 'ease-out' });
  }, [ready, geo]);

  useEffect(() => {
    if (ready) (mapRef.current!.getSource('regions') as GeoJSONSource).setData(regionsToGeoJson(regions));
  }, [ready, regions]);

  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    map.setFilter('region-selected', ['==', ['get', 'id'], selectedRegion]);
    map.setProjection({ type: globe ? 'globe' : 'mercator' });
    const r = regions.find((x) => x.id === selectedRegion);
    const duration = reducedMotion() ? 0 : 700;
    if (globe && (!r || r.id === 'global')) {
      // a whole-world box cannot be fitted on a globe; show one hemisphere instead
      map.easeTo({ center: [0, 15], zoom: 1.4, duration });
      return;
    }
    const bounds = !r || r.id === 'global' ? WORLD : boxBounds(r.box);
    map.fitBounds(bounds, { padding: 24, duration, maxZoom: 3 });
  }, [ready, selectedRegion, regions, globe]);

  return (
    <div className="map-frame">
      <div ref={container} className="map" role="region" aria-label={label} />
      {failed && (
        <div className="map-overlay" role="alert">
          <p>
            This browser cannot draw the map (WebGL is turned off or not supported). The region list and the results
            still work.
          </p>
        </div>
      )}
      {(busy || !ready) && !failed && (
        <div className="map-overlay" role="status">
          <span className="meter" aria-hidden="true">▓▓▓▒▒▒░░░░</span> Loading map…
        </div>
      )}
      {hover && grid && <CellTip hover={hover} grid={grid} unit={unit} />}
    </div>
  );
}

function CellTip({ hover, grid, unit }: { hover: Hover; grid: Grid; unit: string }) {
  const { index: i, region } = hover;
  let body;
  if (i < 0) body = <p>Outside the grid.</p>;
  else {
    const { lat, lon } = cellCenter(i, grid.lat, grid.lon);
    const sig = grid.significant[i];
    const slope = grid.slope[i];
    body = (
      <>
        <p className="tip__where">CELL {fmtLatLon(lat, lon)}</p>
        {slope === null || sig === null ? (
          <p>No data or too little data here.</p>
        ) : (
          <>
            <p className="tip__value">
              {sig === 1 && slope > 0 ? '▲ ' : sig === 1 && slope < 0 ? '▼ ' : ''}{fmtSigned(slope)} {unit} per decade
            </p>
            <p>
              95% CI {fmtSigned(grid.ci_low[i])} to {fmtSigned(grid.ci_high[i])}
            </p>
            <p className={sig ? 'tip__sig' : 'tip__nosig'}>
              {sig ? '● Significant' : '○ Not significant'} (q = {fmt(grid.q[i], 2)})
            </p>
          </>
        )}
      </>
    );
  }
  // keep the tip inside the map: open towards the center
  const style: React.CSSProperties = {
    left: hover.x,
    top: hover.y,
    transform: `translate(${hover.x > hover.w / 2 ? 'calc(-100% - 12px)' : '12px'}, ${hover.y > hover.h / 2 ? 'calc(-100% - 12px)' : '12px'})`,
  };
  return (
    <div className="tip" style={style} aria-hidden="true">
      {body}
      {region && <p className="tip__region">→ Click to select {region.name}</p>}
    </div>
  );
}
