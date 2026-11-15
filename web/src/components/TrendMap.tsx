import { useEffect, useRef, useState } from 'react';
import maplibregl, { type GeoJSONSource, type Map as MlMap, type StyleSpecification } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import type { Grid, Region } from '../dataClient';
import { boxBounds, cellCenter, cellIndexAt, graticule, regionAt, regionsToGeoJson } from '../mapScale';
// Natural Earth 1:50m land (public domain), simplified by scripts/build-land.mjs; bundled, so no runtime request
import land from '../assets/land-50m.json';
import { reducedMotion } from '../viz';
import { fmt, fmtLatLon, fmtSigned } from '../format';

type Fc = GeoJSON.FeatureCollection;
const EMPTY: Fc = { type: 'FeatureCollection', features: [] };
// map ink (ocean = --map-bg, graticule = --rule, coast and boxes = --text-2, selection = --text in styles/tokens.css)
const INK = { bg: '#050d12', land: '#142832', grid: '#1b2f3a', line: '#b3cbcc', text: '#e4f1ef', selected: '#e4f1ef' };
// data layer opacities when shown; 0 in the overview
const DATA_OPACITY = { 'cells-sig': 0.85, 'cells-nosig': 0.3, glow: 0.22, dots: 0.6 } as const;
const FADE_MS = 400;
const CAMERA_MS = 750;
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
  /** false = overview: the plain basemap with region boxes, no data layer */
  showData: boolean;
  /** removes the data layer (shown only while there is one) */
  onClear: () => void;
  /** dim the boxes that are not selected */
  dimOthers: boolean;
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

export function TrendMap({ grid, geo, unit, regions, selectedRegion, onSelectRegion, globe, showData, onClear, dimOthers, busy, label }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MlMap | null>(null);
  const [ready, setReady] = useState(false);
  const [hover, setHover] = useState<Hover | null>(null);
  const [failed, setFailed] = useState(false);
  // event handlers are bound once; read current values through refs
  const live = useRef({ grid, regions, onSelectRegion, showData });
  live.current = { grid, regions, onSelectRegion, showData };
  const lastGlobe = useRef<boolean | null>(null);

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

    // Sources and layers are added once; selections only change opacity, filters and the camera.
    // Order, bottom to top: ocean, land, graticule, data, coastline, region boxes. The data sits between the land
    // fill and the coastline, so continent outlines stay readable on top of it.
    map.on('load', () => {
      const fade = { duration: 0, delay: 0 }; // set per change in the data effect
      map.addSource('land', { type: 'geojson', data: land as Fc });
      map.addSource('graticule', { type: 'geojson', data: graticule(30) });
      map.addSource('cells', { type: 'geojson', data: EMPTY });
      map.addSource('dots', { type: 'geojson', data: EMPTY });
      map.addSource('regions', { type: 'geojson', data: EMPTY });
      map.addLayer({ id: 'land', type: 'fill', source: 'land', paint: { 'fill-color': INK.land } });
      map.addLayer({ id: 'graticule', type: 'line', source: 'graticule', paint: { 'line-color': INK.line, 'line-opacity': 0.09, 'line-width': 1 } });
      // not significant: faded; significant: nearly opaque plus the dot stipple, so significance never relies on color alone
      for (const [id, sig] of [['cells-nosig', 0], ['cells-sig', 1]] as const)
        map.addLayer({
          id,
          type: 'fill',
          source: 'cells',
          filter: ['==', ['get', 's'], sig],
          paint: { 'fill-color': ['get', 'c'], 'fill-opacity': 0, 'fill-opacity-transition': fade, 'fill-antialias': false },
        });
      // soft glow under significant cells, in their own color
      map.addLayer({
        id: 'glow',
        type: 'circle',
        source: 'dots',
        paint: {
          'circle-color': ['get', 'c'],
          'circle-opacity': 0,
          'circle-opacity-transition': fade,
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
          'circle-opacity': 0,
          'circle-opacity-transition': fade,
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 0, 0.6, 2, 1.1, 5, 2.4],
        },
      });
      // coastline: a dark halo keeps the 1px light line visible over pale data cells too
      map.addLayer({ id: 'coast-halo', type: 'line', source: 'land', paint: { 'line-color': INK.bg, 'line-opacity': 0.7, 'line-width': 3, 'line-blur': 1.5 } });
      map.addLayer({ id: 'coast', type: 'line', source: 'land', paint: { 'line-color': INK.line, 'line-opacity': 0.9, 'line-width': 1 } });
      map.addLayer({
        id: 'regions',
        type: 'line',
        source: 'regions',
        paint: { 'line-color': INK.line, 'line-opacity': 0.45, 'line-opacity-transition': { duration: 300, delay: 0 }, 'line-width': 1, 'line-dasharray': [3, 2] },
      });
      map.addLayer({ id: 'region-selected', type: 'line', source: 'regions', filter: ['==', ['get', 'id'], ''], paint: { 'line-color': INK.selected, 'line-width': 2.5 } });
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
        index: g && live.current.showData ? cellIndexAt(lng, lat, g.lat, g.lon) : -1,
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
    if (!ready || !map || !geo) return;
    (map.getSource('cells') as GeoJSONSource).setData(geo.cells);
    (map.getSource('dots') as GeoJSONSource).setData(geo.dots);
  }, [ready, geo]);

  // fade the data layer in over the basemap, or out in the overview (instant under reduced motion)
  const visible = showData && !!geo;
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    const fade = { duration: reducedMotion() ? 0 : FADE_MS, delay: 0 };
    for (const [id, opacity] of Object.entries(DATA_OPACITY)) {
      const prop = id.startsWith('cells') ? 'fill-opacity' : 'circle-opacity';
      map.setPaintProperty(id, `${prop}-transition`, fade);
      map.setPaintProperty(id, prop, visible ? opacity : 0);
    }
  }, [ready, visible]);

  useEffect(() => {
    if (ready) (mapRef.current!.getSource('regions') as GeoJSONSource).setData(regionsToGeoJson(regions));
  }, [ready, regions]);

  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    map.setFilter('region-selected', ['==', ['get', 'id'], selectedRegion]);
    map.setPaintProperty('regions', 'line-opacity', dimOthers ? 0.15 : 0.45);
  }, [ready, selectedRegion, dimOthers]);

  // Camera: a region choice fits its box; pressing Globe view (on or off) shows the whole world.
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    const globeToggled = lastGlobe.current !== null && lastGlobe.current !== globe;
    lastGlobe.current = globe;
    map.setProjection({ type: globe ? 'globe' : 'mercator' });
    const r = regions.find((x) => x.id === selectedRegion);
    const duration = reducedMotion() ? 0 : CAMERA_MS;
    if (globeToggled || !r || r.id === 'global') {
      // a whole-world box cannot be fitted on a globe; show one hemisphere instead
      if (globe) map.easeTo({ center: [0, 15], zoom: 1.4, duration });
      else map.fitBounds(WORLD, { padding: 24, duration });
      return;
    }
    map.fitBounds(boxBounds(r.box), { padding: 24, duration, maxZoom: 3 });
  }, [ready, selectedRegion, regions, globe]);

  return (
    <div className="map-frame">
      <div ref={container} className="map" role="region" aria-label={label} />
      {showData && !failed && (
        <button type="button" className="btn btn--secondary btn--small map-clear" onClick={onClear}>
          Clear data
        </button>
      )}
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
      {hover && (visible && grid ? <CellTip hover={hover} grid={grid} unit={unit} /> : hover.region && <RegionTip hover={hover} />)}
    </div>
  );
}

// keep the tip inside the map: open towards the center
const tipPosition = (h: Hover): React.CSSProperties => ({
  left: h.x,
  top: h.y,
  transform: `translate(${h.x > h.w / 2 ? 'calc(-100% - 12px)' : '12px'}, ${h.y > h.h / 2 ? 'calc(-100% - 12px)' : '12px'})`,
});

/** Overview tooltip: the region under the pointer. The same choice is in the region list. */
function RegionTip({ hover }: { hover: Hover }) {
  return (
    <div className="tip" style={tipPosition(hover)} aria-hidden="true">
      <p className="tip__value">{hover.region!.name}</p>
      <p>{hover.region!.display_note ?? 'approximate study area'}</p>
      <p className="tip__region">→ Click to select</p>
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
          <p>No data here, or not applicable (for example ocean for a land-only variable).</p>
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
  return (
    <div className="tip" style={tipPosition(hover)} aria-hidden="true">
      {body}
      {region && <p className="tip__region">→ Click to select {region.name}</p>}
    </div>
  );
}
