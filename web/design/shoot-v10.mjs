// Usage: node design/shoot-v10.mjs <outdir>   (dev server on :5173). Compare page, a separate and an overlapping pair.
import { chromium } from '@playwright/test';
const out = process.argv[2];
const B = 'http://localhost:5173/#';
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const PAIRS = [
  ['separate', '/compare?var=t2m&a=mexico&b=sahel'],
  ['overlapping', '/compare?var=t2m&a=western_europe&b=mediterranean'],
];
const errors = [];
for (const [tag, vp] of [['desktop', { width: 1440, height: 900 }], ['phone', { width: 390, height: 844 }]]) {
  const p = await browser.newPage({ viewport: vp });
  p.on('pageerror', (e) => errors.push(`${tag}: ${e.message}`));
  for (const [name, path] of PAIRS) {
    await p.goto('about:blank'); await p.goto(B + path);
    await p.waitForSelector('.recharts-line-curve'); await p.waitForTimeout(800);
    // grow the viewport to the page so responsive charts are measured at their real width
    await p.setViewportSize({ ...vp, height: await p.evaluate(() => document.documentElement.scrollHeight) }); await p.waitForTimeout(800);
    await p.screenshot({ path: `${out}/compare-${name}-${tag}.png` });
    await p.setViewportSize(vp);
  }
  await p.close();
}
console.log(errors.length ? errors.join('\n') : 'shots ok');
await browser.close();
