import { describe, expect, it } from 'vitest';
import { LAYERS, RAMP, frameCodes, globeCells, isLand } from './globe';
import { LAND_ROWS, MASK_H, MASK_W } from './landMask';

describe('land mask', () => {
  it('has the documented size and puts land and sea where they are', () => {
    expect(LAND_ROWS).toHaveLength(MASK_H);
    for (const r of LAND_ROWS) expect(r).toHaveLength(MASK_W / 4);
    const cell = (lat: number, lon: number) =>
      isLand(Math.floor(((90 - lat) * MASK_H) / 180), Math.floor(((lon + 180) * MASK_W) / 360));
    expect(cell(0, 20)).toBe(true); // Central Africa
    expect(cell(-85, 0)).toBe(true); // Antarctica, closed around the pole
    expect(cell(0, -150)).toBe(false); // Pacific
    expect(cell(89, 0)).toBe(false); // Arctic Ocean
  });
});

describe('globe frame', () => {
  const cells = globeCells(40, 20, 6, 12, 120);
  it('fills a disc and uses only valid glyph codes', () => {
    expect(cells.every((k) => (k.c * 6 + 3 - 120) ** 2 + (k.r * 12 + 6 - 120) ** 2 <= 120 ** 2 + 1e-9)).toBe(true);
    for (const v of frameCodes(cells, 0)) {
      expect(v).toBeGreaterThanOrEqual(-1);
      expect(v).toBeLessThan(LAYERS * RAMP.length);
    }
  });
  it('turns: after half a revolution the picture changes, after a full one it is back', () => {
    const a = frameCodes(cells, 0.1).join();
    expect(frameCodes(cells, 0.6).join()).not.toBe(a);
    expect(frameCodes(cells, 1.1).join()).toBe(a);
  });
  it('leaves the hole for the wordmark empty', () => {
    const holed = globeCells(40, 20, 6, 12, 120, { x0: 60, y0: 100, x1: 180, y1: 140 });
    expect(holed.length).toBeLessThan(cells.length);
    expect(holed.some((k) => k.c === 20 && k.r === 10)).toBe(false);
  });
});
