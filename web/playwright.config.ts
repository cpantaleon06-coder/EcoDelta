import { defineConfig } from '@playwright/test';

// Smoke test against the production build, served with the fixture swapped in for the committed real data
// (the tests expect the fixture's regions and values; public/web_data is left untouched).
export default defineConfig({
  testDir: 'e2e',
  timeout: 60_000,
  use: {
    baseURL: 'http://localhost:4173',
    // software WebGL so the map also renders on machines and CI runners without a GPU
    launchOptions: { args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] },
  },
  webServer: {
    command: 'npm run build && rm -rf dist/web_data && cp -r ../ecodelta-engine/web_data_fixture dist/web_data && npm run preview -- --port 4173 --strictPort',
    url: 'http://localhost:4173',
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
