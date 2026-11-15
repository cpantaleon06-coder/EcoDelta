import { describe, expect, it } from 'vitest';
import { applyAction, mapView, readSelection } from './mapState';

const VARS = ['t2m', 'precip'];
const REGIONS = ['global', 'mexico', 'antarctica'];
const read = (q: string) => readSelection(new URLSearchParams(q), VARS, REGIONS);

describe('map selection state', () => {
  it('starts in the overview: no data layer, whole world, no highlight', () => {
    const s = read('');
    expect(s).toEqual({ variable: null, region: 'global' });
    expect(mapView(s)).toEqual({ showData: false, highlight: null, dimOthers: false });
  });
  it('choosing a variable shows the data layer', () => {
    const p = applyAction(new URLSearchParams(''), { type: 'variable', id: 'precip' });
    const s = read(p.toString());
    expect(s.variable).toBe('precip');
    expect(mapView(s)).toEqual({ showData: true, highlight: null, dimOthers: false });
  });
  it('choosing a region highlights its box and dims the others, with or without data', () => {
    const s = read(applyAction(new URLSearchParams(''), { type: 'region', id: 'mexico' }).toString());
    expect(mapView(s)).toEqual({ showData: false, highlight: 'mexico', dimOthers: true });
    expect(mapView(read('var=t2m&region=mexico'))).toEqual({ showData: true, highlight: 'mexico', dimOthers: true });
  });
  it('clear removes the data layer and keeps the region', () => {
    const p = applyAction(new URLSearchParams('var=t2m&region=antarctica'), { type: 'clear' });
    expect(read(p.toString())).toEqual({ variable: null, region: 'antarctica' });
  });
  it('ignores unknown ids', () => {
    expect(read('var=nope&region=atlantis')).toEqual({ variable: null, region: 'global' });
  });
});
