# EcoDelta web

Static, display-only website for EcoDelta (NASA Space Apps 2026). It reads precomputed JSON from the EcoDelta
engine (`public/web_data/`) and computes no statistics in the browser. Vite, React, TypeScript, MapLibre GL JS and
Recharts.

## Data

```bash
npm run sync-data            # copies ../ecodelta-engine/web_data (real data, the default)
npm run sync-data -- fixture # copies ../ecodelta-engine/web_data_fixture (synthetic demo data)
npm run sync-data -- <path>  # any folder that holds engine output
```

The data contract is `../ecodelta-engine/docs/OUTPUT_SCHEMA.md`. Every read goes through `src/dataClient.ts`.

## Build guard

`npm run build` first runs `scripts/data-guard.mjs`. It stops the build when `public/web_data/meta.json` is
missing or holds demo data (`synthetic` is not `false`, or `source` is not `"real"`, the same rule as the DEMO
DATA banner). To build on the fixture on purpose, for a local preview or the end-to-end tests:

```bash
ALLOW_FIXTURE=1 npm run build
```

## Develop and test

```bash
npm install
npm run dev        # http://localhost:5173
npm test           # unit tests (Vitest), including the build guard
npm run test:e2e   # Playwright smoke tests against the production build (uses ALLOW_FIXTURE=1)
npm run lint
```

`design/shoot-v8.mjs` takes the review screenshots (dev server running), and `.audit.mjs` checks text contrast,
sideways overflow, keyboard focus and reduced motion.

## Deploy (Vercel)

`vercel.json` runs `npm run sync-data -- ${ECODELTA_DATA_SOURCE:-real} && npm run build`. With no variable set it
uses the real data, and the build fails if that data is missing or synthetic. A demo deployment needs both
`ECODELTA_DATA_SOURCE=fixture` and `ALLOW_FIXTURE=1`; it then shows the DEMO DATA banner and header badge.

Open problems and unverified points are listed in `PROBLEMS.md`; third-party licenses in `THIRD_PARTY.md`.
