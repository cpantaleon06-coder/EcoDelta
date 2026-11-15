import { describe, expect, it } from 'vitest';
import { coverage, evidenceLabel, findPair, signalsTogether, sourceLine, NA } from './results';
import type { Answers, CompareFile, Provenance } from './dataClient';

const where = (covered: number, valid: number) =>
  ({ n_box_cells: 144, fixed_mask: { n_cells: 40, covered_fraction: covered, n_valid_months: valid, n_months: 297, weight_share_min: 1, weight_share_max: 1 } }) as Answers['where'];

describe('evidenceLabel', () => {
  it('always pairs a symbol with a word', () => {
    expect(evidenceLabel('strong')).toEqual({ symbol: '●●●', text: 'Strong evidence' });
    expect(evidenceLabel('none').text).toBe('No evidence of a trend');
    expect(evidenceLabel('insufficient data').text).toBe('Insufficient data');
    expect(evidenceLabel(undefined).text).toBe(`Evidence: ${NA}`);
  });
});

describe('coverage', () => {
  it('describes cells and months and warns below the engine thresholds', () => {
    const ok = coverage(where(0.9, 297))!;
    expect(ok.spatial).toBe('40 of 144 grid cells, 90% of the study area');
    expect(ok.temporal).toBe('297 of 297 months');
    expect(ok.warnings).toEqual([]);
    expect(coverage(where(0.25, 200))!.warnings).toHaveLength(2);
    expect(coverage({ n_box_cells: 4 } as Answers['where'])).toBeNull();
  });
});

describe('sourceLine', () => {
  it('uses provenance and says not available for missing values', () => {
    expect(sourceLine({ product_short_name: 'M2TMNXSLV', version: '5.12.4', period: ['2001-01', '2025-09'] } as Provenance)).toBe(
      'Source: M2TMNXSLV, version 5.12.4, 2001-01 to 2025-09',
    );
    expect(sourceLine({ product_short_name: 'X', version: null, period: null } as Provenance)).toBe(`Source: X, version ${NA}, period ${NA}`);
    expect(sourceLine(undefined)).toBe(`Source: ${NA}`);
  });
});

describe('signalsTogether', () => {
  it('lists only moderate or strong trends with a direction, and never names a cause', () => {
    const s = signalsTogether([
      { name: 'Air temperature', evidence: 'strong', direction: 'increase' },
      { name: 'Water in the topsoil', evidence: 'moderate', direction: 'decrease' },
      { name: 'Rain', evidence: 'weak', direction: 'increase' },
    ]);
    expect(s).toBe('Signals found together: air temperature: increasing; water in the topsoil: decreasing.');
    expect(signalsTogether([{ name: 'Rain', evidence: 'none', direction: 'none detected' }])).toMatch(/^No variable/);
    expect(s).not.toMatch(/cause|because|due to|driv/i);
  });
});

describe('findPair', () => {
  it('finds a pair in either order and keeps the file order', () => {
    const file = { pairs: [{ region_a: 'global', region_b: 'mexico' }] } as CompareFile;
    expect(findPair(file, 'mexico', 'global')?.region_a).toBe('global');
    expect(findPair(file, 'global', 'sahel')).toBeUndefined();
  });
});
