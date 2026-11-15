// Ship the license texts that bundled code and the font require (BSD-3-Clause for maplibre-gl, OFL-1.1 for the font).
// The minified bundle drops their comments, so the texts go to public/licenses/ and from there into dist/.
import { copyFileSync, mkdirSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const web = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const dest = `${web}/public/licenses`;
const files = {
  'maplibre-gl.txt': 'node_modules/maplibre-gl/LICENSE.txt',
  'poppins-OFL.txt': 'node_modules/@fontsource/poppins/LICENSE',
};
mkdirSync(dest, { recursive: true });
for (const [name, src] of Object.entries(files)) copyFileSync(`${web}/${src}`, `${dest}/${name}`);
console.log(`Copied ${Object.keys(files).length} license files to public/licenses/`);
