// Usage: node design/compare.mjs [set]   Builds compare[-set]-{desktop,phone}.png from design/before and design/<set> (default after).
import { chromium } from '@playwright/test';
import { writeFileSync, rmSync } from 'node:fs';
const dir = new URL('.', import.meta.url).pathname;
const after = process.argv[2] ?? 'after';
const views = ['explore', 'detail', 'guided-1', 'guided-3', 'guided-4', 'about'];
const sets = { desktop: views, phone: views };
const b = await chromium.launch();
for (const [tag, views] of Object.entries(sets)) {
  const w = tag === 'desktop' ? 720 : 300;
  const rows = views.map((v) => `<h2>${v}</h2><div class=row><figure><figcaption>before</figcaption><img src="before/${v}-${tag}.png"></figure><figure><figcaption>${after}</figcaption><img src="${after}/${v}-${tag}.png"></figure></div>`).join('');
  writeFileSync(`${dir}.cmp-${tag}.html`, `<!doctype html><style>body{margin:0;padding:16px;background:#222;color:#eee;font:14px monospace}h2{margin:16px 0 6px;font-size:14px}.row{display:flex;gap:16px;align-items:flex-start}figure{margin:0;width:${w}px}img{width:100%;display:block;border:1px solid #555}</style>${rows}`);
  const p = await b.newPage({ viewport: { width: 2 * w + 48, height: 800 } });
  await p.goto(`file://${dir}.cmp-${tag}.html`); await p.waitForLoadState('load');
  await p.screenshot({ path: `${dir}compare${after === 'after' ? '' : `-${after}`}-${tag}.png`, fullPage: true });
  rmSync(`${dir}.cmp-${tag}.html`);
}
await b.close();
