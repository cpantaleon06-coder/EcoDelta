// Usage: node design/shoot-v9.mjs <outdir>   (dev server on :5173). Map states for the basemap pass.
import { chromium } from '@playwright/test';
const out = process.argv[2];
const B = 'http://localhost:5173/#';
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const settled = (p) => p.waitForFunction(() => document.querySelector('.map canvas') && !document.querySelector('.map-overlay'), null, { timeout: 30000 }).then(() => p.waitForTimeout(2000));
const STATES = [
  ['overview', '/explore'],
  ['variable-global', '/explore?region=global&var=t2m'],
  ['region-mexico', '/explore?region=mexico&var=t2m'],
  ['region-antarctica', '/explore?region=antarctica&var=evap'],
];
const errors = [];
for (const [tag, vp] of [['desktop', { width: 1440, height: 900 }], ['phone', { width: 390, height: 844 }]]) {
  const p = await browser.newPage({ viewport: vp });
  p.on('pageerror', (e) => errors.push(`${tag}: ${e.message}`));
  p.on('request', (r) => { if (!/^(data|blob):|^http:\/\/localhost/.test(r.url())) errors.push(`${tag}: external request ${r.url()}`); });
  for (const [name, path] of STATES) {
    await p.goto('about:blank'); await p.goto(B + path); await settled(p);
    await p.locator('#map').scrollIntoViewIfNeeded(); await p.waitForTimeout(400);
    await p.locator('#map').screenshot({ path: `${out}/${name}-${tag}.png` });
  }
  await p.close();
}
console.log(errors.length ? errors.join('\n') : 'shots ok');
await browser.close();
