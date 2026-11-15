import { describe, expect, it } from 'vitest';
import { checkData } from '../scripts/data-guard.mjs';
import { isDemoData, type Meta } from './dataClient';

const real = { source: 'real', synthetic: false };
const fixture = { source: 'fixture', synthetic: true };

describe('build data guard', () => {
  it('passes real data and blocks the fixture unless ALLOW_FIXTURE is set', () => {
    expect(checkData(real, false)).toBeNull();
    expect(checkData(fixture, false)).toMatch(/demo data/);
    expect(checkData(fixture, true)).toBeNull();
  });
  it('blocks a missing meta.json even with ALLOW_FIXTURE', () => {
    expect(checkData(null, true)).toMatch(/missing/);
  });
  it('uses the same demo rule as the app', () => {
    for (const m of [real, fixture, { source: 'real', synthetic: true }, { source: 'fixture', synthetic: false }, { source: 'real' }])
      expect(checkData(m, false) !== null).toBe(isDemoData(m as Meta));
  });
});
