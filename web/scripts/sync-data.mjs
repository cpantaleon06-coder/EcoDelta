// Copy engine output into public/web_data/.
// Usage: npm run sync-data [-- real | fixture | <path to a web_data folder>]   (default: real)
import { cpSync, existsSync, rmSync, readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const engine = resolve(here, '../../ecodelta-engine');
const arg = process.argv[2] ?? 'real';
const src = { fixture: `${engine}/web_data_fixture`, real: `${engine}/web_data` }[arg] ?? resolve(arg);
const dest = resolve(here, '../public/web_data');

if (!existsSync(`${src}/meta.json`)) {
  console.error(`No meta.json in ${src}. Pass "fixture", "real" or a folder that holds engine output.`);
  process.exit(1);
}
rmSync(dest, { recursive: true, force: true });
cpSync(src, dest, { recursive: true });
const meta = JSON.parse(readFileSync(`${dest}/meta.json`, 'utf8'));
console.log(`Copied ${src} -> ${dest}`);
console.log(`source=${meta.source} synthetic=${meta.synthetic} period=${meta.period.start}..${meta.period.end} schema=${meta.schema_version}`);
