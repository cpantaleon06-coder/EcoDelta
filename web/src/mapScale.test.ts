import { describe, expect, it } from 'vitest';
import type { Axis, Grid, Region } from './dataClient';
import {
  PALETTE as P,
  absPercentile,
  cellCenter,
  cellIndexAt,
  colorFor,
  gridToGeoJson,
  niceCeil,
  regionAt,
  symmetricMax,
} from './mapScale';

const LAT: Axis = { first: -89, last: 89, step: 2, n: 90 };
const LON: Axis = { first: -179, last: 179, step: 2, n: 180 };

describe('color scale', () => {
  it('ignores nulls in the percentile and returns null with no values', () => {
    expect(absPercentile([null, -4, 2, null, 1, 3], 100)).toBe(4);
    expect(absPercentile([null, 1, -3], 50)).toBe(2);
    expect(absPercentile([null, null], 95)).toBeNull();
  });
  it('rounds the legend limit up to 2 significant digits', () => {
    expect(niceCeil(0.0437)).toBeCloseTo(0.044);
    expect(niceCeil(0.92)).toBeCloseTo(0.92);
    expect(niceCeil(0)).toBe(1);
    expect(symmetricMax([null, null])).toBe(1);
  });
  it('is centered on zero, symmetric and clamps beyond the limit', () => {
    expect(colorFor(0, 1, P)).toBe(P[4]);
    expect(colorFor(0.99, 1, P)).toBe(P[8]);
    expect(colorFor(-0.99, 1, P)).toBe(P[0]);
    expect(colorFor(50, 1, P)).toBe(P[8]);
    expect(colorFor(-50, 1, P)).toBe(P[0]);
    expect(P.indexOf(colorFor(0.5, 1, P)) - 4).toBe(4 - P.indexOf(colorFor(-0.5, 1, P)));
  });
});

describe('grid cells', () => {
  it('finds row-major cell indexes and wraps longitude', () => {
    expect(cellIndexAt(-179.5, -89.5, LAT, LON)).toBe(0);
    expect(cellIndexAt(179.9, 89.9, LAT, LON)).toBe(90 * 180 - 1);
    expect(cellIndexAt(181, -89, LAT, LON)).toBe(cellIndexAt(-179, -89, LAT, LON));
    expect(cellIndexAt(0, 95, LAT, LON)).toBe(-1);
    expect(cellCenter(181, LAT, LON)).toEqual({ lat: -87, lon: -177 });
  });
  it('skips no-data cells and dots only significant cells', () => {
    const n = 90 * 180;
    const grid = {
      variable: 't2m',
      lat: LAT,
      lon: LON,
      slope: Array(n).fill(null),
      significant: Array(n).fill(null),
    } as unknown as Grid;
    const i = cellIndexAt(-100, 20, LAT, LON);
    const j = cellIndexAt(10, 15, LAT, LON);
    grid.slope[i] = 0.3;
    grid.significant[i] = 1;
    grid.slope[j] = -0.1;
    grid.significant[j] = 0;
    const { cells, dots } = gridToGeoJson(grid, 0.5, P);
    expect(cells.features).toHaveLength(2);
    expect(dots.features).toHaveLength(1);
    expect(cells.features.map((f) => f.properties!.s).sort()).toEqual([0, 1]);
  });
});

describe('regionAt', () => {
  const regions: Region[] = [
    { id: 'global', name: 'Global', phrase: 'the whole globe', box: [-90, 90, -180, 180] },
    { id: 'arctic', name: 'Arctic', phrase: 'the Arctic', box: [66.5, 90, -180, 180] },
    { id: 'siberia', name: 'Siberia', phrase: 'Siberia', box: [50, 75, 60, 180] },
  ];
  it('picks the smallest box and never global', () => {
    expect(regionAt(100, 70, regions)?.id).toBe('siberia');
    expect(regionAt(0, 80, regions)?.id).toBe('arctic');
    expect(regionAt(0, 0, regions)).toBeUndefined();
  });
});
