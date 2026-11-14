import { describe, expect, it } from 'vitest';
import { badgeFor, describeValue, fmt, fmtP, fmtPercent, fmtSigned, fmtTick, humanizeKey } from './format';

describe('fmt', () => {
  it('keeps 3 significant digits with trailing zeros, like the engine sentences', () => {
    expect(fmt(0.5004)).toBe('0.500');
    expect(fmtSigned(0.2029)).toBe('+0.203');
    expect(fmtSigned(-0.004618)).toBe('−0.00462');
    expect(fmt(-0.00006026)).toBe('−0.0000603');
    expect(fmt(1234.5)).toBe('1235');
  });
  it('handles null, undefined, NaN and zero', () => {
    expect(fmt(null)).toBe('n/a');
    expect(fmtSigned(undefined)).toBe('n/a');
    expect(fmt(NaN)).toBe('n/a');
    expect(fmtSigned(0)).toBe('0');
  });
  it('formats p-values, percents and axis ticks', () => {
    expect(fmtP(7.7e-5)).toBe('< 0.001');
    expect(fmtP(0.241)).toBe('= 0.24');
    expect(fmtP(null)).toBe('n/a');
    expect(fmtPercent(0.2569)).toBe('26%');
    expect(fmtPercent(null)).toBe('n/a');
    expect(fmtTick(0.6)).toBe('0.6');
    expect(fmtTick(-1.2)).toBe('−1.2');
    expect(fmtTick(0)).toBe('0');
  });
});

describe('labels', () => {
  it('humanizes method keys and values', () => {
    expect(humanizeKey('ci_level')).toBe('CI level');
    expect(describeValue(['2001-01', '2025-09'])).toBe('2001-01 to 2025-09');
    expect(describeValue({ method: 'Benjamini-Hochberg', q: 0.05 })).toBe('Method: Benjamini-Hochberg; Q: 0.05');
  });
  it('never labels insufficient data as significant', () => {
    expect(badgeFor({ tier: 2, significant: true }).text).toBe('Not enough data');
    expect(badgeFor({ tier: 1, significant: false }).text).toBe('Not significant');
    expect(badgeFor({ tier: 0, significant: true }).text).toBe('Significant');
  });
});
