import { afterEach, describe, expect, it, vi } from 'vitest';
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { isDemoData, type Grid, type Meta, type RegionDetail, type Screening } from './dataClient';

const respond = (body: unknown, status = 200) =>
  vi.fn().mockResolvedValue({ ok: status < 400, status, json: async () => body });

// fresh module per test so the request cache starts empty
const client = async () => {
  vi.resetModules();
  return import('./dataClient');
};

afterEach(() => vi.unstubAllGlobals());

describe('loading', () => {
  it('accepts schema 1.x and caches the request', async () => {
    const fetch = respond({ schema_version: '1.2.0', source: 'real', synthetic: false });
    vi.stubGlobal('fetch', fetch);
    const c = await client();
    expect((await c.loadMeta()).source).toBe('real');
    await c.loadMeta();
    expect(fetch).toHaveBeenCalledTimes(1);
  });
  it('rejects an unsupported schema version', async () => {
    vi.stubGlobal('fetch', respond({ schema_version: '2.0.0' }));
    await expect((await client()).loadMeta()).rejects.toThrow(/unsupported schema_version 2.0.0/);
  });
  it('explains a missing file and allows a retry', async () => {
    const fetch = respond({}, 404);
    vi.stubGlobal('fetch', fetch);
    const c = await client();
    await expect(c.loadMeta()).rejects.toThrow(/HTTP 404.*sync-data/);
    await expect(c.loadMeta()).rejects.toThrow();
    expect(fetch).toHaveBeenCalledTimes(2);
  });
  it('refuses ids that are not plain identifiers', async () => {
    vi.stubGlobal('fetch', respond({ schema_version: '1.0.0' }));
    await expect((await client()).loadGrid('../meta')).rejects.toThrow(/Invalid data path/);
  });
});

describe('demo banner rule', () => {
  const meta = (source: string, synthetic: boolean) => ({ source, synthetic }) as Meta;
  it('shows the banner unless the data is real and not synthetic', () => {
    expect(isDemoData(meta('real', false))).toBe(false);
    expect(isDemoData(meta('fixture', true))).toBe(true);
    expect(isDemoData(meta('real', true))).toBe(true);
    expect(isDemoData(meta('fixture', false))).toBe(true);
    expect(isDemoData({ source: 'real' } as Meta)).toBe(true); // missing flag counts as demo
  });
});

// The engine's fixture follows the same contract as real data; check the shapes the app relies on.
const FIXTURE = resolve(__dirname, '../../ecodelta-engine/web_data_fixture');
const read = <T>(p: string): T => JSON.parse(readFileSync(`${FIXTURE}/${p}`, 'utf8'));

describe.skipIf(!existsSync(FIXTURE))('engine fixture matches what the app reads', () => {
  const meta = read<Meta>('meta.json');
  it('has grids with one value per cell for every included variable', () => {
    for (const v of meta.variables_included) {
      const g = read<Grid>(`grids/${v}.json`);
      const n = g.lat.n * g.lon.n;
      for (const k of ['slope', 'ci_low', 'ci_high', 'p', 'q', 'significant', 'n_valid'] as const) expect(g[k]).toHaveLength(n);
      expect(g.significant.every((s) => s === 0 || s === 1 || s === null)).toBe(true);
    }
  });
  it('has region series aligned with dates, and screening ranks 1..n', () => {
    const r = read<RegionDetail>('regions/mexico.json');
    for (const v of Object.values(r.variables)) {
      if (v.series) expect(v.series.anomaly).toHaveLength(r.dates.length);
    }
    const s = read<Screening>('screening/mexico.json');
    expect(s.ranking.map((x) => x.rank)).toEqual(s.ranking.map((_, i) => i + 1));
  });
  it('has no estimate exactly when the verdict is insufficient data', () => {
    const r = read<RegionDetail>('regions/antarctica.json');
    for (const v of Object.values(r.variables)) {
      const none = v.answers.what.verdict === 'insufficient data';
      expect(v.answers.how_much.slope_per_decade === null).toBe(none);
    }
  });
});
