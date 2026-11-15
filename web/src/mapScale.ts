// Pure helpers for the trend map: color scale, grid cell geometry, region lookup. No statistics here:
// every number drawn comes straight from the grid file.
import type { Axis, Grid, Region } from './dataClient';

// 9-class diverging scale made for a dark map (own values, no borrowed palette), ordered negative -> positive:
// blue for a decrease, green for an increase, the same for every variable. The middle class is a dark neutral so
// near-zero cells recede, and lightness grows toward both ends, so the two sides also differ for color-blind readers.
export const PALETTE = ['#c3dcff', '#7fb0f7', '#4180d6', '#24508f', '#1b2a33', '#1f5c4c', '#2e9470', '#5cd394', '#c2f5b8'];

/** p-th percentile (0..100) of |values|, ignoring nulls; linear interpolation. null if no values. */
export function absPercentile(values: (number | null)[], p: number): number | null {
  const a = values.filter((v): v is number => v !== null && Number.isFinite(v)).map(Math.abs).sort((x, y) => x - y);
  if (!a.length) return null;
  const pos = (p / 100) * (a.length - 1);
  const lo = Math.floor(pos);
  return a[lo] + (a[Math.min(lo + 1, a.length - 1)] - a[lo]) * (pos - lo);
}

/** Round up to a "nice" legend limit with 2 significant digits (0.0437 -> 0.044). */
export function niceCeil(x: number): number {
  if (!(x > 0)) return 1;
  const mag = 10 ** (Math.floor(Math.log10(x)) - 1);
  return Math.ceil(x / mag - 1e-9) * mag;
}

/** Symmetric color domain [-max, max] from the 95th percentile of |slope|, so a few extreme cells do not wash out the map. */
export function symmetricMax(slopes: (number | null)[]): number {
  return niceCeil(absPercentile(slopes, 95) ?? 0);
}

/** Color of one value on a symmetric classed scale; values beyond ±max take the end colors. */
export function colorFor(value: number, max: number, palette: string[]): string {
  const n = palette.length;
  const k = Math.floor(((value + max) / (2 * max)) * n);
  return palette[Math.max(0, Math.min(n - 1, k))];
}

const cellIndex1d = (v: number, axis: Axis) => {
  const i = Math.floor((v - (axis.first - axis.step / 2)) / axis.step);
  return i >= 0 && i < axis.n ? i : -1;
};

/** Flat row-major index of the cell that contains (lng, lat), or -1 outside the grid. */
export function cellIndexAt(lng: number, lat: number, lat_axis: Axis, lon_axis: Axis): number {
  const lngWrapped = ((((lng + 180) % 360) + 360) % 360) - 180;
  const i = cellIndex1d(lat, lat_axis);
  const j = cellIndex1d(lngWrapped, lon_axis);
  return i < 0 || j < 0 ? -1 : i * lon_axis.n + j;
}

export const cellCenter = (index: number, lat: Axis, lon: Axis) => ({
  lat: lat.first + Math.floor(index / lon.n) * lat.step,
  lon: lon.first + (index % lon.n) * lon.step,
});

// Web Mercator ends at ±85.0511° (where the world becomes a square). Cell polygons, boxes and the graticule are clipped
// exactly there, so the row centered at ±85 reaches the map edge and the rows at ±87 and ±89 are not drawn.
// The land polygons go to ±90 and MapLibre clamps them at the same latitude, so cells and coastlines line up.
const MAX_LAT = 85.0511;
const clampLat = (v: number) => Math.max(-MAX_LAT, Math.min(MAX_LAT, v));

type Fc = GeoJSON.FeatureCollection;

/** Polygons for cells with a slope (colored, faded if not significant) and points at significant cells (stipple). */
export function gridToGeoJson(grid: Grid, max: number, palette: string[]): { cells: Fc; dots: Fc } {
  const cells: GeoJSON.Feature[] = [];
  const dots: GeoJSON.Feature[] = [];
  const h = grid.lat.step / 2;
  const w = grid.lon.step / 2;
  grid.slope.forEach((s, i) => {
    if (s === null || grid.significant[i] === null) return; // no data: leave blank
    const { lat, lon } = cellCenter(i, grid.lat, grid.lon);
    const s0 = clampLat(lat - h);
    const n0 = clampLat(lat + h);
    if (s0 === n0) return;
    const sig = grid.significant[i] === 1 ? 1 : 0;
    cells.push({
      type: 'Feature',
      properties: { c: colorFor(s, max, palette), s: sig },
      geometry: { type: 'Polygon', coordinates: [[[lon - w, s0], [lon + w, s0], [lon + w, n0], [lon - w, n0], [lon - w, s0]]] },
    });
    if (sig && Math.abs(lat) < MAX_LAT) dots.push({ type: 'Feature', properties: { c: colorFor(s, max, palette) }, geometry: { type: 'Point', coordinates: [lon, lat] } });
  });
  return { cells: { type: 'FeatureCollection', features: cells }, dots: { type: 'FeatureCollection', features: dots } };
}

/** Meridians and parallels every `step` degrees (drawn under the data as a faint reference grid). */
export function graticule(step = 30): Fc {
  const line = (coordinates: [number, number][]): GeoJSON.Feature => ({ type: 'Feature', properties: {}, geometry: { type: 'LineString', coordinates } });
  const features: GeoJSON.Feature[] = [];
  for (let lon = -180; lon <= 180; lon += step) features.push(line([[lon, -MAX_LAT], [lon, 0], [lon, MAX_LAT]]));
  for (let lat = -90 + step; lat < 90; lat += step) features.push(line([[-180, lat], [0, lat], [180, lat]]));
  return { type: 'FeatureCollection', features };
}

const boxArea = ([s, n, w, e]: Region['box']) => (n - s) * (e - w);

/** The smallest region box (other than "global") that contains the point, or undefined. */
export function regionAt(lng: number, lat: number, regions: Region[]): Region | undefined {
  return regions
    .filter((r) => r.id !== 'global')
    .filter(({ box: [s, n, w, e] }) => lat >= s && lat <= n && lng >= w && lng <= e)
    .sort((a, b) => boxArea(a.box) - boxArea(b.box))[0];
}

export function regionsToGeoJson(regions: Region[]): Fc {
  return {
    type: 'FeatureCollection',
    features: regions
      .filter((r) => r.id !== 'global')
      .map((r) => {
        const [s0, n0, w, e] = r.box;
        const s = clampLat(s0);
        const n = clampLat(n0);
        return {
          type: 'Feature',
          properties: { id: r.id },
          geometry: { type: 'Polygon', coordinates: [[[w, s], [e, s], [e, n], [w, n], [w, s]]] },
        };
      }),
  };
}

/** [[west, south], [east, north]] for fitBounds. */
export const boxBounds = ([s, n, w, e]: Region['box']): [[number, number], [number, number]] => [
  [w, clampLat(s)],
  [e, clampLat(n)],
];
