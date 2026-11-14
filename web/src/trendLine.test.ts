import { describe, expect, it } from 'vitest';
import { barGeometry, displayTrend, yearTicks } from './trendLine';

describe('display trend line', () => {
  it('passes through zero mid-period and changes by the slope per decade', () => {
    const n = 241; // 20 years of months, middle at index 120
    expect(displayTrend(0.3, 120, n)).toBeCloseTo(0);
    expect(displayTrend(0.3, n - 1, n) - displayTrend(0.3, 0, n)).toBeCloseTo(0.6); // 20 years = 2 decades
    expect(displayTrend(-0.3, 0, n)).toBeCloseTo(0.3);
  });
  it('ticks January of every 5th year', () => {
    expect(yearTicks(['2004-12', '2005-01', '2005-02', '2010-01', '2011-01'])).toEqual([1, 3]);
  });
});

describe('total change bar', () => {
  it('starts at zero (50%) and keeps the whisker inside the track', () => {
    const g = barGeometry(0.5, 0.26, 0.74);
    expect(g.barStart).toBe(50);
    expect(g.barEnd).toBeGreaterThan(50);
    expect(g.ciEnd).toBeLessThan(100);
    const neg = barGeometry(-0.2, -0.4, 0.1);
    expect(neg.barEnd).toBe(50);
    expect(neg.ciStart).toBeGreaterThan(0);
    expect(barGeometry(0, 0, 0).value).toBe(50);
  });
});
