import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  // relative asset paths so the same build works on Vercel and on a GitHub Pages subpath
  base: './',
  // the Explore chunk is ~1 MB because maplibre-gl alone is ~800 kB; it loads only on that page
  build: { chunkSizeWarningLimit: 1200 },
  test: { include: ['src/**/*.test.ts'] },
});
