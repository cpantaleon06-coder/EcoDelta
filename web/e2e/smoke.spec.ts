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
