import { defineConfig } from '@playwright/test';

// Smoke test against the production build. Run "npm run sync-data -- fixture" first; ALLOW_FIXTURE=1 lets the build use it.
export default defineConfig({
  testDir: 'e2e',
  timeout: 60_000,
  use: {
    baseURL: 'http://localhost:4173',
    // software WebGL so the map also renders on machines and CI runners without a GPU
    launchOptions: { args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] },
  },
  webServer: {
    command: 'ALLOW_FIXTURE=1 npm run build && npm run preview -- --port 4173 --strictPort',
    url: 'http://localhost:4173',
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
