// Usage: node design/shoot-v8.mjs <outdir>   (dev server on :5173). Views for the content and honesty pass.
import { chromium } from '@playwright/test';
const out = process.argv[2];
const B = 'http://localhost:5173/#';
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const mapReady = (p) => p.waitForFunction(() => document.querySelector('.map canvas') && !document.querySelector('.map-overlay'), null, { timeout: 30000 }).then(() => p.waitForTimeout(1500));
const errors = [];
for (const [tag, vp] of [['desktop', { width: 1440, height: 900 }], ['phone', { width: 390, height: 844 }]]) {
  const p = await browser.newPage({ viewport: vp });
  p.on('pageerror', (e) => errors.push(`${tag}: ${e.message}`));
  p.on('request', (r) => { if (!r.url().startsWith('http://localhost') && !/^(data|blob):/.test(r.url())) errors.push(`${tag}: external request ${r.url()}`); });
  await p.goto(B + '/explore?region=mexico&var=t2m'); await mapReady(p);
  await p.screenshot({ path: `${out}/explore-${tag}.png` });
  await p.locator('.explore__panel').screenshot({ path: `${out}/ranking-${tag}.png` });
  await p.locator('#profile').scrollIntoViewIfNeeded(); await p.waitForTimeout(400);
  await p.locator('#profile').screenshot({ path: `${out}/profile-${tag}.png` });
  await p.locator('.research-note summary').click(); await p.waitForTimeout(300);
  await p.locator('.research-note').screenshot({ path: `${out}/research-note-${tag}.png` });
  await p.goto('about:blank'); await p.goto(B + '/compare?var=t2m&a=mexico&b=global');
  await p.waitForSelector('.recharts-line-curve'); await p.waitForTimeout(600);
  await p.setViewportSize({ ...vp, height: await p.evaluate(() => document.documentElement.scrollHeight) }); await p.waitForTimeout(800);
  await p.screenshot({ path: `${out}/compare-${tag}.png` });
  await p.setViewportSize(vp);
  await p.goto('about:blank'); await p.goto(B + '/about'); await p.waitForSelector('#provenance');
  await p.locator('#provenance').scrollIntoViewIfNeeded(); await p.waitForTimeout(400);
  await p.locator('section:has(#provenance)').screenshot({ path: `${out}/about-provenance-${tag}.png` });
  const overflow = await p.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
  if (overflow) errors.push(`${tag}: horizontal page scroll on About`);
  await p.close();
}
console.log(errors.length ? errors.join('\n') : 'shots ok');
await browser.close();
