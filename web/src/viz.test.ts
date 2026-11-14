import { describe, expect, it } from 'vitest';
import { classEdges, sparkPoints, stripeColors, yearlyValues } from './viz';
import { PALETTE as P, colorFor, graticule } from './mapScale';

describe('classEdges', () => {
  it('splits -max..max into the classes colorFor uses', () => {
    const e = classEdges(0.9);
    expect(e).toHaveLength(10);
    expect(e[0]).toBeCloseTo(-0.9);
    expect(e[9]).toBeCloseTo(0.9);
    for (let k = 0; k < 9; k++) expect(colorFor((e[k] + e[k + 1]) / 2, 0.9, P)).toBe(P[k]);
  });
});

describe('yearlyValues', () => {
  it('takes the December running mean and skips years without one', () => {
    const dates = ['2001-11', '2001-12', '2002-06', '2002-12', '2003-01', '2003-12'];
    expect(yearlyValues(dates, [1, 2, 3, null, 5, 6])).toEqual([
      { year: 2001, value: 2 },
      { year: 2003, value: 6 },
    ]);
  });
});

describe('sparkPoints', () => {
  it('puts min at the bottom, max at the top, and a flat series in the middle', () => {
    expect(sparkPoints([0, 1, 0.5], 10, 10)).toBe('0.0,9.0 5.0,1.0 10.0,5.0');
    expect(sparkPoints([2, 2], 10, 10)).toBe('0.0,5.0 10.0,5.0');
  });
});

describe('stripeColors', () => {
  it('is symmetric around zero', () => {
    expect(stripeColors([-1, 0, 1], P)).toEqual([P[0], P[4], P[8]]);
    expect(stripeColors([0, 0], P)).toEqual([P[4], P[4]]);
  });
});

describe('graticule', () => {
  it('draws meridians and parallels, never at the poles', () => {
    const g = graticule(30);
    expect(g.features).toHaveLength(13 + 5);
  });
});
