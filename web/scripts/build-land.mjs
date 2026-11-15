// Usage: node scripts/build-land.mjs   Writes src/assets/land-50m.json, the land polygons of the map basemap and
// (via build-landmask.mjs) of the hero globe. Run once; the output is committed.
// Source: Natural Earth 1:50m land (public domain), via the world-atlas package (ISC).
// Simplified with Douglas-Peucker (0.04 degree) and rounded to 0.01 degree: the data cells are 2 degrees wide.
import { readFileSync, writeFileSync } from 'node:fs';
import { feature } from 'topojson-client';

const TOLERANCE = 0.04;
const topo = JSON.parse(readFileSync(new URL('../node_modules/world-atlas/land-50m.json', import.meta.url)));

// A ring edge that jumps across the dateline (Antarctica) is closed around the pole instead of straight across
// the map, so a flat (lon/lat or Mercator) fill covers the land down to the pole.
const closeAtPole = (r) =>
  r.flatMap((p, i) => {
    const q = r[i + 1];
    if (!q || Math.abs(q[0] - p[0]) <= 180) return [p];
    const e = Math.sign(p[0]) * 180;
    const pole = p[1] < 0 ? -90 : 90;
    return [p, [e, p[1]], [e, pole], [-e, pole], [-e, q[1]]];
  });

// Douglas-Peucker on the lon/lat plane, iterative
function simplify(pts) {
  if (pts.length < 5) return pts;
  const keep = new Uint8Array(pts.length);
  keep[0] = keep[pts.length - 1] = 1;
  const stack = [[0, pts.length - 1]];
  while (stack.length) {
    const [a, b] = stack.pop();
    const [ax, ay] = pts[a];
    const [bx, by] = pts[b];
    const dx = bx - ax;
    const dy = by - ay;
    const len = Math.hypot(dx, dy) || 1;
    let worst = -1;
    let dmax = 0;
    for (let i = a + 1; i < b; i++) {
      const d = Math.abs(dy * (pts[i][0] - ax) - dx * (pts[i][1] - ay)) / len;
      if (d > dmax) [dmax, worst] = [d, i];
    }
    if (dmax > TOLERANCE) {
      keep[worst] = 1;
      stack.push([a, worst], [worst, b]);
    }
  }
  return pts.filter((_, i) => keep[i]);
}

const round = ([x, y]) => [Math.round(x * 100) / 100, Math.round(y * 100) / 100];
// a closed ring starts and ends on the same point, so split it at the point farthest from the start
const simplifyRing = (r) => {
  const m = r.reduce((k, p, i) => (Math.hypot(p[0] - r[0][0], p[1] - r[0][1]) > Math.hypot(r[k][0] - r[0][0], r[k][1] - r[0][1]) ? i : k), 0);
  return [...simplify(r.slice(0, m + 1)), ...simplify(r.slice(m)).slice(1)];
};
const ring = (r) => {
  const out = simplifyRing(closeAtPole(r)).map(round);
  return out.filter((p, i) => i === 0 || p[0] !== out[i - 1][0] || p[1] !== out[i - 1][1]);
};

const polygons = feature(topo, topo.objects.land)
  .features.flatMap((f) => (f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.coordinates))
  .map((poly) => poly.map(ring).filter((r) => r.length >= 4))
  .filter((poly) => poly.length);

const geo = { type: 'FeatureCollection', features: [{ type: 'Feature', properties: {}, geometry: { type: 'MultiPolygon', coordinates: polygons } }] };
const json = JSON.stringify(geo);
writeFileSync(new URL('../src/assets/land-50m.json', import.meta.url), json);
const points = polygons.flat(2).length;
console.log(`polygons: ${polygons.length}, points: ${points}, size: ${(json.length / 1024).toFixed(0)} KB`);
