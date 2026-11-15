import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

// Automated WCAG 2.1 A/AA rules only; this is not a screen reader test.
// Reduced motion so axe measures the settled page, not rows halfway through their fade-in.
test.use({ reducedMotion: 'reduce' });
const PAGES: [string, string, string][] = [
  ['explore', './#/explore', 'h1'],
  ['profile and detail (Arctic)', './#/explore?region=arctic&var=t2m', '#detail-title'],
  ['compare (overlapping pair)', './#/compare?var=t2m&a=western_europe&b=mediterranean', '.compare__diff-title'],
  ['about', './#/about', 'h1'],
];

for (const [name, url, ready] of PAGES) {
  test(`axe: ${name}`, async ({ page }) => {
    await page.goto(url);
    await expect(page.locator(ready).first()).toBeVisible();
    const { violations } = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze();
    const found = violations.map((v) => `${v.id} (${v.impact}): ${v.nodes.length} node(s), e.g. ${v.nodes[0]?.target.join(' ')}`);
    expect(found, found.join('\n')).toEqual([]);
  });
}

test('polar regions stay reachable outside the map', async ({ page }) => {
  await page.goto('./#/explore?region=antarctica');
  await expect(page.getByRole('heading', { name: /What changed across Antarctica/ })).toBeVisible();
  const panel = page.getByRole('complementary', { name: 'Ranking for the selected region' });
  await panel.getByRole('button', { name: /Air temperature/ }).click();
  await expect(page.locator('#detail-title')).toContainText('Antarctica');
  await expect(page.getByText(/cells above about 85 degrees latitude/)).toBeVisible();
});
