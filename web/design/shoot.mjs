// Usage: node design/shoot.mjs <outdir>   (dev server on :5173). Same views for before/after comparisons.
import { chromium } from '@playwright/test';
const out = process.argv[2];
const B = 'http://localhost:5173/#';
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const mapReady = (p) => p.waitForFunction(() => document.querySelector('.map canvas') && !document.querySelector('.map-overlay'), null, { timeout: 30000 }).then(() => p.waitForTimeout(1500));
const guided = async (p, step) => {
  await p.goto('about:blank'); await p.goto(B + '/guided'); await p.waitForSelector('input[name=var]', { state: 'attached' });
  if (step === 1) return;
  await p.getByLabel('Air temperature near the ground').check();
  await p.getByRole('button', { name: /Next/ }).click();
  await p.getByLabel('Mexico', { exact: true }).check();
  await p.getByRole('button', { name: /Next/ }).click();
  await p.waitForSelector('.recharts-line-curve'); await p.waitForTimeout(900);
  if (step === 3) return;
  await p.getByRole('button', { name: /Next/ }).click(); await p.waitForTimeout(500);
};
const errors = [];
for (const [tag, vp] of [['desktop', { width: 1440, height: 900 }], ['phone', { width: 390, height: 844 }]]) {
  const p = await browser.newPage({ viewport: vp });
  p.on('pageerror', (e) => errors.push(`${tag}: ${e.message}`));
  await p.goto(B + '/explore?region=mexico&var=t2m'); await mapReady(p);
  await p.screenshot({ path: `${out}/explore-${tag}.png` });
  await p.locator('#detail').scrollIntoViewIfNeeded(); await p.waitForTimeout(600);
  await p.locator('#detail').screenshot({ path: `${out}/detail-${tag}.png` });
  for (const s of [1, 3, 4]) {
    await guided(p, s);
    // grow the viewport to the page instead of fullPage, so responsive charts are measured at their real width
    if (s !== 1) { await p.setViewportSize({ ...vp, height: await p.evaluate(() => document.documentElement.scrollHeight) }); await p.waitForTimeout(800); }
    await p.screenshot({ path: `${out}/guided-${s}-${tag}.png` });
    await p.setViewportSize(vp);
  }
  await p.goto('about:blank'); await p.goto(B + '/about'); await p.waitForTimeout(1200);
  await p.screenshot({ path: `${out}/about-${tag}.png` });
  await p.close();
}
console.log(errors.length ? errors.join('\n') : 'shots ok');
await browser.close();
