// First step of "npm run build": refuse to ship a production build on demo data.
// ALLOW_FIXTURE=1 lets the fixture through (local previews, e2e tests).
import { existsSync, readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

/** Same rule as isDemoData in src/dataClient.ts. Returns an error message, or null when the build may go on. */
export function checkData(meta, allowFixture) {
  if (!meta) return 'public/web_data/meta.json is missing. Run "npm run sync-data" first.';
  const demo = meta.synthetic !== false || meta.source !== 'real';
  if (demo && !allowFixture)
    return `public/web_data holds demo data (source=${meta.source}, synthetic=${meta.synthetic}). ` +
      'Run "npm run sync-data -- real", or set ALLOW_FIXTURE=1 to build on the fixture on purpose.';
  return null;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const file = resolve(dirname(fileURLToPath(import.meta.url)), '../public/web_data/meta.json');
  const meta = existsSync(file) ? JSON.parse(readFileSync(file, 'utf8')) : null;
  const error = checkData(meta, process.env.ALLOW_FIXTURE === '1');
  if (error) {
    console.error(`Build stopped: ${error}`);
    process.exit(1);
  }
  console.log(`Data check: source=${meta.source} synthetic=${meta.synthetic}${process.env.ALLOW_FIXTURE === '1' ? ' (ALLOW_FIXTURE=1)' : ''}`);
}
