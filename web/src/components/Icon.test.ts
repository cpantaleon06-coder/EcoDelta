import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { ICON_NAMES, Icon, type IconName } from './Icon';
import { varIcon } from '../viz';

const html = (props: { name: IconName; title?: string; decorative?: boolean }) => renderToStaticMarkup(createElement(Icon, props));

describe('Icon', () => {
  it('draws every icon on the 24px grid with paths inside it', () => {
    for (const name of ICON_NAMES) {
      const svg = html({ name });
      expect(svg).toContain('viewBox="0 0 24 24"');
      for (const [, d] of svg.matchAll(/ d="([^"]+)"/g))
        for (const n of d.match(/-?\d+(\.\d+)?/g)!.map(Number)) expect(Math.abs(n)).toBeLessThanOrEqual(24);
    }
  });
  it('is hidden from assistive technology unless it has a title', () => {
    expect(html({ name: 'map' })).toContain('aria-hidden="true"');
    const named = html({ name: 'significant', title: 'Significant' });
    expect(named).toContain('role="img"');
    expect(named).toContain('aria-label="Significant"');
    expect(named).not.toContain('aria-hidden');
    expect(html({ name: 'info', title: 'Info', decorative: true })).toContain('aria-hidden="true"');
  });
  it('has a drawing for each of the five variables', () => {
    for (const id of ['t2m', 'precip', 'evap', 'runoff_surface', 'soil_moisture_0_10cm']) expect(varIcon(id)).toBeDefined();
    expect(varIcon('unknown')).toBeUndefined();
  });
});
