import { expect, test } from '@playwright/test';

test('load, select Mexico, open a variable, chart renders', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));

  await page.goto('./');
  await expect(page.getByRole('heading', { level: 1 })).toContainText('What changed on Earth');
  await expect(page.locator('.map canvas')).toBeVisible();

  await page.getByLabel('Region', { exact: true }).selectOption({ label: 'Mexico' });
  await expect(page.getByRole('heading', { name: /What changed across Mexico/ })).toBeVisible();

  await page.getByRole('complementary', { name: 'Ranking for the selected region' }).getByRole('button', { name: /Rain and snow/ }).click();
  await expect(page).toHaveURL(/region=mexico/);
  await expect(page).toHaveURL(/var=precip/);
  await expect(page.locator('#detail-title')).toContainText('Rain and snow (precipitation) across Mexico');
  await expect(page.locator('.chart .recharts-line-curve').first()).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Is it significant?' })).toBeVisible();

  expect(errors).toEqual([]);
});

test('shows the DEMO DATA banner only for synthetic data', async ({ page, request }) => {
  const meta = await (await request.get('./web_data/meta.json')).json();
  await page.goto('./#/about');
  await expect(page.getByRole('heading', { name: 'Data products' })).toBeVisible();
  const demo = meta.synthetic !== false || meta.source !== 'real';
  await expect(page.getByRole('note').getByText('DEMO DATA')).toHaveCount(demo ? 1 : 0);
});

test('hero: decorative globe is hidden from screen readers, Explore the map moves focus to the controls', async ({ page }) => {
  await page.goto('./#/explore');
  await expect(page.locator('.globe-wrap')).toHaveAttribute('aria-hidden', 'true');
  await expect(page.locator('canvas.globe')).toBeVisible();
  await page.getByRole('button', { name: 'Explore the map' }).click();
  await expect(page.getByLabel('Variable', { exact: true })).toBeFocused();
});

test('ranking: evidence and magnitude stay separate, sort toggle, profile and research note', async ({ page }) => {
  await page.goto('./#/explore?region=mexico&var=t2m');
  const panel = page.getByRole('complementary', { name: 'Ranking for the selected region' });
  await expect(panel.getByText('approximate study area')).toBeVisible();
  const byMagnitude = panel.getByRole('button', { name: 'By magnitude', exact: true });
  await byMagnitude.click();
  await expect(byMagnitude).toHaveAttribute('aria-pressed', 'true');
  await expect(panel.locator('.rank-row').first().locator('.evidence')).toBeVisible();
  await expect(panel.locator('.rank-row').first().locator('.cibar')).toBeAttached();
  await expect(panel.locator('.source-line').first()).toContainText('Source:');

  await expect(page.getByText('This shows what changed together, not what caused what.')).toBeVisible();
  await page.getByText('Research note').click();
  for (const part of ['Finding', 'Evidence', 'Coverage', 'Limitations', 'What we cannot conclude'])
    await expect(page.locator('.research-note dt', { hasText: part })).toBeVisible();
});

test('compare: verdict, required caveats, overlap caution, difference series', async ({ page }) => {
  await page.goto('./#/compare?var=t2m&a=mexico&b=sahel');
  await expect(page.getByRole('heading', { name: /^Verdict:/ })).toBeVisible();
  await expect(page.getByText('Overlapping regions, interpret with caution')).toHaveCount(0);
  await page.goto('./#/compare?var=t2m&a=mexico&b=global');
  await expect(page.getByRole('heading', { name: /^Verdict:/ })).toBeVisible();
  await expect(page.getByText('A trend that is significant in one region and not in the other does not show that the two trends differ.')).toBeVisible();
  await expect(page.getByText('Looking at many pairs raises the chance of false positives.')).toBeVisible();
  await expect(page.getByText('Overlapping regions, interpret with caution')).toBeVisible();
  await expect(page.locator('.callout--warn')).toContainText('Shared cells do not fully cancel');
  await expect(page.getByText(/the shared cells cancel in the difference/)).toHaveCount(0);
  // global comes first in the file, so the difference is Global minus Mexico
  await expect(page.getByRole('heading', { name: /^Difference series: Global minus Mexico$/ })).toBeVisible();
  await expect(page.getByRole('img', { name: /monthly difference .* with the trend of the difference/ })).toBeVisible();
  await page.getByLabel('Region B').selectOption({ label: 'Mexico' });
  await expect(page.getByText('Choose two different regions.')).toBeVisible();
});

test('about: provenance table, engine commit and manifest hash', async ({ page }) => {
  await page.goto('./#/about');
  await expect(page.getByRole('heading', { name: 'Data provenance' })).toBeVisible();
  await expect(page.locator('details.prov[open] th', { hasText: 'Statistical method' })).toBeVisible();
  await expect(page.getByText(/Manifest hash \(SHA-256\):/)).toBeVisible();
});

test('map: overview basemap first, data after choosing a variable, Clear data returns to the overview', async ({ page }) => {
  await page.goto('./#/explore');
  await expect(page.getByText('Pick a variable or a region to see how it changed.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Clear data' })).toHaveCount(0);
  await page.getByLabel('Variable', { exact: true }).selectOption({ label: 'Air temperature near the ground' });
  await expect(page).toHaveURL(/var=t2m/);
  await expect(page.getByRole('figure', { name: 'Map legend' })).toBeVisible();
  await page.getByLabel('Region', { exact: true }).selectOption({ label: 'Mexico' });
  await page.getByRole('button', { name: 'Clear data' }).click();
  await expect(page).not.toHaveURL(/var=/);
  await expect(page).toHaveURL(/region=mexico/);
  await expect(page.getByText('Pick a variable or a region to see how it changed.')).toBeVisible();
});
