import { chromium } from '@playwright/test';
const [out] = process.argv.slice(2);
const b = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
for (const [tag, vp] of [['desktop', { width: 1440, height: 900 }], ['phone', { width: 390, height: 844 }]]) {
  const p = await b.newPage({ viewport: vp });
  const errs = []; p.on('pageerror', (e) => errs.push(e.message)); p.on('console', (m) => m.type() === 'error' && errs.push(m.text()));
  await p.goto('http://localhost:5173/#/explore?region=mexico&var=t2m');
  await p.waitForFunction(() => document.querySelector('.map canvas') && !document.querySelector('.map-overlay') && document.querySelector('.scoreboard'), null, { timeout: 30000 });
  await p.waitForTimeout(1500);
  await p.locator('.explore__map').screenshot({ path: `${out}/map-${tag}.png` });
  await p.locator('.explore__panel').screenshot({ path: `${out}/rank-${tag}.png` });
  await p.locator('.explore__board').screenshot({ path: `${out}/board-${tag}.png` });
  const over = await p.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  console.log(tag, 'overflow', over, errs.join(' | ') || 'no errors');
  await p.close();
}
await b.close();
