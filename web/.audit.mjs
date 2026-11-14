// Ad-hoc a11y/responsive audit: text contrast (WCAG AA), horizontal overflow, visible keyboard focus, hero globe motion.
import { chromium } from '@playwright/test';
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const B = 'http://localhost:5173/#';
const states = [
  ['explore-mexico', '/explore?region=mexico&var=t2m', null],
  ['explore-antarctica', '/explore?region=antarctica&var=evap', null],
  ['guided-1', '/guided', null],
  ['guided-3', '/guided', async (p) => { await p.getByLabel('Rain and snow (precipitation)').check(); await p.getByRole('button', { name: 'Next' }).click(); await p.getByLabel('Mexico').check(); await p.getByRole('button', { name: 'Next' }).click(); await p.waitForSelector('.tcb'); }],
  ['guided-4', '/guided', async (p) => { await p.getByLabel('Rain and snow (precipitation)').check(); await p.getByRole('button', { name: 'Next' }).click(); await p.getByLabel('Mexico').check(); await p.getByRole('button', { name: 'Next' }).click(); await p.waitForSelector('.tcb'); await p.getByRole('button', { name: 'Next' }).click(); }],
  ['about', '/about', null],
];
const contrastCheck = () => {
  const lum = (c) => { const [r, g, b] = c.map((v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; }); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
  const parse = (s) => (s.match(/[\d.]+/g) || []).map(Number);
  const bgOf = (el) => { for (let e = el; e; e = e.parentElement) { const c = parse(getComputedStyle(e).backgroundColor); if (c.length === 3 || c[3] > 0.5) return c.slice(0, 3); } return [255, 255, 255]; };
  const out = new Set();
  for (const el of document.querySelectorAll('body *')) {
    if (el.closest('svg, .maplibregl-map, .sr-only, .corners')) continue;
    if (getComputedStyle(el).backgroundClip === 'text') continue; // decorative loading meter
    const hasText = [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim());
    if (!hasText) continue;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none' || el.closest('[disabled]')) continue;
    let op = 1; for (let e = el; e; e = e.parentElement) op *= Number(getComputedStyle(e).opacity);
    const fg = parse(cs.color); const bg = bgOf(el);
    const a = (fg[3] ?? 1) * op; const mix = fg.slice(0, 3).map((v, i) => v * a + bg[i] * (1 - a));
    const [l1, l2] = [lum(mix), lum(bg)].sort((x, y) => y - x);
    const ratio = (l1 + 0.05) / (l2 + 0.05);
    const size = parseFloat(cs.fontSize); const bold = Number(cs.fontWeight) >= 700;
    const need = size >= 24 || (bold && size >= 18.66) ? 3 : 4.5;
    if (ratio < need) out.add(`${ratio.toFixed(2)} < ${need}: "${el.textContent.trim().slice(0, 40)}" ${cs.color} on rgb(${bg})`);
  }
  // chart text drawn in SVG: fill against the panel behind the chart
  for (const t of document.querySelectorAll('.chart svg text')) {
    const cs = getComputedStyle(t); const fg = parse(cs.fill); const bg = bgOf(t.closest('.chart'));
    if (fg.length < 3) continue;
    const [l1, l2] = [lum(fg), lum(bg)].sort((x, y) => y - x); const ratio = (l1 + 0.05) / (l2 + 0.05);
    if (ratio < 4.5) out.add(`${ratio.toFixed(2)} < 4.5: svg "${t.textContent.trim().slice(0, 20)}" ${cs.fill} on rgb(${bg})`);
  }
  return [...out];
};
for (const width of process.env.GLOBE_ONLY ? [] : [360, 390, 768, 1024, 1366]) {
  for (const [name, url, act] of states) {
    const page = await browser.newPage({ viewport: { width, height: 900 } });
    const errs = []; page.on('pageerror', (e) => errs.push(e.message));
    await page.goto(B + url); await page.waitForTimeout(1500);
    if (act) await act(page);
    await page.waitForTimeout(800);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    const contrast = width === 1366 || width === 390 ? await page.evaluate(contrastCheck) : [];
    let noFocus = [];
    if (width === 1366) {
      for (let i = 0; i < (name.startsWith('explore') ? 160 : 45); i++) {
        await page.keyboard.press('Tab');
        const r = await page.evaluate(() => { const e = document.activeElement; if (!e || e === document.body) return null; const cs = getComputedStyle(e); const ring = (x) => x && getComputedStyle(x).outlineStyle !== 'none' && parseFloat(getComputedStyle(x).outlineWidth) > 0; const visible = ring(e) || ring(e.closest('.choice')); return visible ? null : `${e.tagName}.${e.className}:${(e.textContent || e.getAttribute('aria-label') || '').trim().slice(0, 25)}`; });
        if (r) noFocus.push(r);
      }
      noFocus = [...new Set(noFocus)];
    }
    const issues = [overflow > 0 && `overflow ${overflow}px`, ...contrast, ...noFocus.map((x) => `no focus ring: ${x}`), ...errs].filter(Boolean);
    console.log(`${width} ${name}: ${issues.length ? '\n  ' + issues.join('\n  ') : 'ok'}`);
    await page.close();
  }
}
// globe: count draws (clearRect on canvas.globe) and time each draw (clearRect to its last fillText)
const instrument = () => {
  window.__g = { draws: [], cur: null };
  const proto = CanvasRenderingContext2D.prototype;
  const clear = proto.clearRect;
  const fill = proto.fillText;
  proto.clearRect = function (...a) {
    if (this.canvas.classList.contains('globe')) { const t = performance.now(); window.__g.cur = { t, end: t }; window.__g.draws.push(window.__g.cur); }
    return clear.apply(this, a);
  };
  proto.fillText = function (...a) {
    const r = fill.apply(this, a);
    if (this.canvas.classList.contains('globe') && window.__g.cur) window.__g.cur.end = performance.now();
    return r;
  };
  const image = proto.drawImage;
  proto.drawImage = function (...a) {
    const r = image.apply(this, a);
    if (this.canvas.classList.contains('globe') && window.__g.cur) window.__g.cur.end = performance.now();
    return r;
  };
};
const globeStats = (p, ms) =>
  p.evaluate(async (ms) => {
    const start = window.__g.draws.length;
    const gaps = [];
    let last = performance.now();
    const t0 = last;
    await new Promise((done) => {
      const f = (now) => { gaps.push(now - last); last = now; if (now - t0 < ms) requestAnimationFrame(f); else done(); };
      requestAnimationFrame(f);
    });
    const d = window.__g.draws.slice(start);
    const cost = d.map((x) => x.end - x.t).sort((a, b) => a - b);
    return { draws: d.length, fps: +(d.length / (ms / 1000)).toFixed(1), drawMsMedian: +(cost[cost.length >> 1] ?? 0).toFixed(2), drawMsMax: +(cost.at(-1) ?? 0).toFixed(2), browserFramesOver50ms: gaps.filter((g) => g > 50).length };
  }, ms);
for (const [tag, vp, cpu] of [['desktop', { width: 1440, height: 900 }, 1], ['phone, CPU 4x slower', { width: 390, height: 844 }, 4]]) {
  const p = await browser.newPage({ viewport: vp });
  await p.addInitScript(instrument);
  const cdp = await p.context().newCDPSession(p);
  await cdp.send('Emulation.setCPUThrottlingRate', { rate: cpu });
  await p.goto(B + '/explore'); await p.waitForSelector('canvas.globe'); await p.waitForTimeout(1500);
  console.log(`globe ${tag}, visible:`, JSON.stringify(await globeStats(p, 3000)));
  await p.evaluate(() => window.scrollTo(0, document.body.scrollHeight)); await p.waitForTimeout(400);
  console.log(`globe ${tag}, scrolled off-screen:`, JSON.stringify(await globeStats(p, 1500)));
  await p.evaluate(() => { window.scrollTo(0, 0); Object.defineProperty(document, 'hidden', { configurable: true, get: () => true }); document.dispatchEvent(new Event('visibilitychange')); });
  await p.waitForTimeout(400);
  console.log(`globe ${tag}, tab hidden:`, JSON.stringify(await globeStats(p, 1500)));
  await p.close();
}
// reduced motion: no running CSS animations, and the globe draws a still frame only
{
  const ctx = await browser.newContext({ reducedMotion: 'reduce', viewport: { width: 1366, height: 900 } });
  const p = await ctx.newPage();
  await p.addInitScript(instrument);
  await p.goto(B + '/explore?region=mexico&var=t2m'); await p.waitForSelector('canvas.globe'); await p.waitForTimeout(1500);
  const before = await p.evaluate(() => window.__g.draws.length);
  const s = await globeStats(p, 2000);
  const anims = await p.evaluate(() => document.getAnimations().filter((a) => a.playState === 'running').length);
  console.log('reduced motion:', JSON.stringify({ globeDrawsBeforeIdle: before, globeDrawsDuring2s: s.draws, runningCssAnimations: anims }));
  await ctx.close();
}
await browser.close();
