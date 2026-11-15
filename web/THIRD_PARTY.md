# Third-party code, assets and licenses

## Borrowed code and assets

| What | Where it is used | License |
|---|---|---|
| Poppins font (The Poppins Project Authors, github.com/itfoundry/Poppins), via @fontsource/poppins | The only typeface of the site, including chart labels and the hero globe characters; Latin subset, weights 400, 600 and 700, woff2, self-hosted | OFL-1.1 |
| Natural Earth 1:50m land (naturalearthdata.com), via world-atlas 2.0.2 (Michael Bostock) | `src/assets/land-50m.json`: land and coastlines of the map basemap, simplified to 0.04 degree and rounded to 0.01 degree by `scripts/build-land.mjs` (373 KB, 122 KB gzipped). `src/hero/landMask.ts`, the 1 degree land mask of the decorative hero globe, is made from the same file by `scripts/build-landmask.mjs` | Data: public domain. Package: ISC |

Only the generated files ship with the site; world-atlas and topojson-client (ISC) are development dependencies used to build them. No country borders are drawn: the app's regions are approximate boxes, and borders would suggest a precision they do not have. Credit: "Made with Natural Earth".

The font is OFL-1.1, not MIT or Apache-2.0. The design brief asked for it by name, which overrides the MIT/Apache-2.0 rule for it.
The map palette in `src/mapScale.ts` is our own set of hex values; the earlier ColorBrewer palettes are no longer used.
There are no NASA logos or insignia.

## License texts shipped with the site

The minified bundle drops license comments (checked: none of MapLibre's survive in `dist/`).
So `scripts/copy-licenses.mjs` runs before every build and copies the MapLibre BSD-3-Clause text and the Poppins OFL text into `public/licenses/`, which ends up in `dist/licenses/`. The About page links to them.

## Note on MapLibre GL JS

`maplibre-gl` is BSD-3-Clause, not MIT or Apache-2.0. It is part of the required stack, so it stays.
BSD-3-Clause is permissive: it asks to keep its copyright notice and not to use the authors names for endorsement.

## Direct dependencies

| Package | Version | License | Role |
|---|---|---|---|
| @fontsource/poppins | 5.3.0 | OFL-1.1 | The one font (self-hosted) |
| maplibre-gl | 5.24.1 | BSD-3-Clause | Map rendering |
| react | 19.3.1 | MIT | UI |
| react-dom | 19.3.1 | MIT | UI |
| react-router-dom | 7.18.5 | MIT | Page routing |
| recharts | 2.15.4 | MIT | Charts |
| @eslint/js | 9.39.5 | MIT | Development only |
| @playwright/test | 1.65.1 | Apache-2.0 | Development only |
| @types/react | 19.3.0 | MIT | Development only |
| @types/react-dom | 19.3.0 | MIT | Development only |
| @vitejs/plugin-react | 4.7.0 | MIT | Development only |
| eslint | 9.39.5 | MIT | Development only |
| eslint-plugin-react-hooks | 5.2.0 | MIT | Development only |
| eslint-plugin-react-refresh | 0.4.26 | MIT | Development only |
| globals | 14.0.0 | MIT | Development only |
| topojson-client | 3.1.0 | ISC | Decodes world-atlas when building the mask (build time only) |
| typescript | 5.8.3 | Apache-2.0 | Development only |
| typescript-eslint | 8.72.2 | MIT | Development only |
| vite | 6.4.6 | MIT | Development only |
| vitest | 3.2.7 | MIT | Development only |
| world-atlas | 2.0.2 | ISC | Land data for the hero globe mask (build time only) |

## All packages shipped in the website (production tree, 75 packages)

License count: MIT: 43, ISC: 20, BSD-3-Clause: 6, BSD-2-Clause: 3, OFL-1.1: 1, (MIT OR Apache-2.0): 1, MIT AND ISC: 1.

| Package | Version | License |
|---|---|---|
| @babel/runtime | 7.29.14 | MIT |
| @fontsource/poppins | 5.3.0 | OFL-1.1 |
| @mapbox/jsonlint-lines-primitives | 2.0.3 | MIT |
| @mapbox/point-geometry | 1.1.0 | ISC |
| @mapbox/tiny-sdf | 2.3.0 | BSD-2-Clause |
| @mapbox/unitbezier | 0.0.1 | BSD-2-Clause |
| @mapbox/unitbezier | 1.0.0 | BSD-2-Clause |
| @mapbox/vector-tile | 2.0.5 | BSD-3-Clause |
| @mapbox/whoots-js | 3.1.0 | ISC |
| @maplibre/geojson-vt | 6.3.1 | ISC |
| @maplibre/maplibre-gl-style-spec | 24.10.0 | ISC |
| @maplibre/mlt | 1.3.0 | (MIT OR Apache-2.0) |
| @maplibre/vt-pbf | 4.3.3 | MIT |
| @types/d3-array | 3.2.2 | MIT |
| @types/d3-color | 3.1.3 | MIT |
| @types/d3-ease | 3.0.2 | MIT |
| @types/d3-interpolate | 3.0.4 | MIT |
| @types/d3-path | 3.1.1 | MIT |
| @types/d3-scale | 4.0.9 | MIT |
| @types/d3-shape | 3.2.0 | MIT |
| @types/d3-time | 3.0.4 | MIT |
| @types/d3-timer | 3.0.2 | MIT |
| @types/geojson | 7946.0.16 | MIT |
| clsx | 2.1.1 | MIT |
| cookie | 1.1.1 | MIT |
| csstype | 3.2.3 | MIT |
| d3-array | 3.2.5 | ISC |
| d3-color | 3.1.1 | ISC |
| d3-ease | 3.0.2 | BSD-3-Clause |
| d3-format | 3.1.3 | ISC |
| d3-interpolate | 3.0.2 | ISC |
| d3-path | 3.1.1 | ISC |
| d3-scale | 4.0.3 | ISC |
| d3-shape | 3.2.1 | ISC |
| d3-time | 3.1.1 | ISC |
| d3-time-format | 4.1.1 | ISC |
| d3-timer | 3.0.2 | ISC |
| decimal.js-light | 2.5.1 | MIT |
| dom-helpers | 5.2.1 | MIT |
| earcut | 3.2.4 | ISC |
| eventemitter3 | 4.0.7 | MIT |
| fast-equals | 5.4.5 | MIT |
| gl-matrix | 3.4.4 | MIT |
| internmap | 2.0.3 | ISC |
| js-tokens | 4.0.0 | MIT |
| json-stringify-pretty-compact | 4.0.0 | MIT |
| kdbush | 4.1.0 | ISC |
| lodash | 4.18.1 | MIT |
| loose-envify | 1.4.0 | MIT |
| maplibre-gl | 5.24.1 | BSD-3-Clause |
| minimist | 1.2.8 | MIT |
| murmurhash-js | 1.0.0 | MIT |
| object-assign | 4.1.1 | MIT |
| pbf | 4.0.2 | BSD-3-Clause |
| pbf | 5.1.2 | BSD-3-Clause |
| potpack | 2.1.0 | ISC |
| prop-types | 15.8.1 | MIT |
| protocol-buffers-schema | 3.6.1 | MIT |
| quickselect | 3.0.0 | ISC |
| react | 19.3.1 | MIT |
| react-dom | 19.3.1 | MIT |
| react-is | 16.13.1 | MIT |
| react-is | 18.3.1 | MIT |
| react-router | 7.18.5 | MIT |
| react-router-dom | 7.18.5 | MIT |
| react-smooth | 4.0.4 | MIT |
| react-transition-group | 4.4.5 | BSD-3-Clause |
| recharts | 2.15.4 | MIT |
| recharts-scale | 0.4.5 | MIT |
| resolve-protobuf-schema | 2.1.0 | MIT |
| scheduler | 0.28.0 | MIT |
| set-cookie-parser | 2.7.3 | MIT |
| tiny-invariant | 1.3.3 | MIT |
| tinyqueue | 3.0.0 | ISC |
| victory-vendor | 36.9.2 | MIT AND ISC |

## All development-only packages (208 packages, not shipped)

License count: MIT: 164, Apache-2.0: 19, ISC: 14, BSD-2-Clause: 6, BSD-3-Clause: 2, Python-2.0: 1, CC-BY-4.0: 1, BlueOak-1.0.0: 1. `caniuse-lite` (CC-BY-4.0) is browser support data used only at build time.

| Package | Version | License |
|---|---|---|
| @babel/code-frame | 7.29.7 | MIT |
| @babel/compat-data | 7.29.7 | MIT |
| @babel/core | 7.29.13 | MIT |
| @babel/generator | 7.29.14 | MIT |
| @babel/helper-compilation-targets | 7.29.13 | MIT |
| @babel/helper-globals | 7.29.7 | MIT |
| @babel/helper-module-imports | 7.29.7 | MIT |
| @babel/helper-module-transforms | 7.29.14 | MIT |
| @babel/helper-plugin-utils | 7.29.7 | MIT |
| @babel/helper-string-parser | 7.29.14 | MIT |
| @babel/helper-validator-identifier | 7.29.7 | MIT |
| @babel/helper-validator-option | 7.29.7 | MIT |
| @babel/helpers | 7.29.14 | MIT |
| @babel/parser | 7.29.14 | MIT |
| @babel/plugin-transform-react-jsx-self | 7.29.7 | MIT |
| @babel/plugin-transform-react-jsx-source | 7.29.7 | MIT |
| @babel/template | 7.29.7 | MIT |
| @babel/traverse | 7.29.14 | MIT |
| @babel/types | 7.29.14 | MIT |
| @esbuild/linux-x64 | 0.25.12 | MIT |
| @eslint-community/eslint-utils | 4.10.1 | MIT |
| @eslint-community/regexpp | 4.12.3 | MIT |
| @eslint/config-array | 0.21.2 | Apache-2.0 |
| @eslint/config-helpers | 0.4.2 | Apache-2.0 |
| @eslint/core | 0.17.0 | Apache-2.0 |
| @eslint/eslintrc | 3.3.7 | MIT |
| @eslint/js | 9.39.5 | MIT |
| @eslint/object-schema | 2.1.7 | Apache-2.0 |
| @eslint/plugin-kit | 0.4.1 | Apache-2.0 |
| @humanfs/core | 0.19.2 | Apache-2.0 |
| @humanfs/node | 0.16.8 | Apache-2.0 |
| @humanfs/types | 0.15.0 | Apache-2.0 |
| @humanwhocodes/module-importer | 1.0.1 | Apache-2.0 |
| @humanwhocodes/retry | 0.4.3 | Apache-2.0 |
| @jridgewell/gen-mapping | 0.3.13 | MIT |
| @jridgewell/remapping | 2.3.5 | MIT |
| @jridgewell/resolve-uri | 3.1.3 | MIT |
| @jridgewell/sourcemap-codec | 1.6.0 | MIT |
| @jridgewell/trace-mapping | 0.3.31 | MIT |
| @playwright/test | 1.65.1 | Apache-2.0 |
| @rolldown/pluginutils | 1.0.0-beta.27 | MIT |
| @rollup/rollup-linux-x64-gnu | 4.68.3 | MIT |
| @rollup/rollup-linux-x64-musl | 4.68.3 | MIT |
| @types/babel__core | 7.20.5 | MIT |
| @types/babel__generator | 7.27.0 | MIT |
| @types/babel__template | 7.4.4 | MIT |
| @types/babel__traverse | 7.28.0 | MIT |
| @types/chai | 5.2.3 | MIT |
| @types/deep-eql | 4.0.2 | MIT |
| @types/estree | 1.0.10 | MIT |
| @types/json-schema | 7.0.15 | MIT |
| @types/react | 19.3.0 | MIT |
| @types/react-dom | 19.3.0 | MIT |
| @typescript-eslint/eslint-plugin | 8.72.2 | MIT |
| @typescript-eslint/parser | 8.72.2 | MIT |
| @typescript-eslint/project-service | 8.72.2 | MIT |
| @typescript-eslint/scope-manager | 8.72.2 | MIT |
| @typescript-eslint/tsconfig-utils | 8.72.2 | MIT |
| @typescript-eslint/type-utils | 8.72.2 | MIT |
| @typescript-eslint/types | 8.72.2 | MIT |
| @typescript-eslint/typescript-estree | 8.72.2 | MIT |
| @typescript-eslint/utils | 8.72.2 | MIT |
| @typescript-eslint/visitor-keys | 8.72.2 | MIT |
| @vitejs/plugin-react | 4.7.0 | MIT |
| @vitest/expect | 3.2.7 | MIT |
| @vitest/mocker | 3.2.7 | MIT |
| @vitest/pretty-format | 3.2.7 | MIT |
| @vitest/runner | 3.2.7 | MIT |
| @vitest/snapshot | 3.2.7 | MIT |
| @vitest/spy | 3.2.7 | MIT |
| @vitest/utils | 3.2.7 | MIT |
| acorn | 8.19.0 | MIT |
| acorn-jsx | 5.3.2 | MIT |
| ajv | 6.15.0 | MIT |
| ansi-styles | 4.3.0 | MIT |
| argparse | 2.0.1 | Python-2.0 |
| assertion-error | 2.0.1 | MIT |
| balanced-match | 1.0.2 | MIT |
| balanced-match | 4.0.4 | MIT |
| baseline-browser-mapping | 2.11.37 | Apache-2.0 |
| brace-expansion | 1.1.22 | MIT |
| brace-expansion | 5.0.13 | MIT |
| browserslist | 4.29.5 | MIT |
| cac | 6.7.14 | MIT |
| callsites | 3.1.0 | MIT |
| caniuse-lite | 1.0.30001826 | CC-BY-4.0 |
| chai | 5.3.3 | MIT |
| chalk | 4.1.2 | MIT |
| check-error | 2.1.3 | MIT |
| color-convert | 2.0.1 | MIT |
| color-name | 1.1.4 | MIT |
| commander | 2.20.3 | MIT |
| concat-map | 0.0.1 | MIT |
| convert-source-map | 2.0.0 | MIT |
| cross-spawn | 7.0.6 | MIT |
| debug | 4.4.3 | MIT |
| deep-eql | 5.0.2 | MIT |
| deep-is | 0.1.4 | MIT |
| electron-to-chromium | 1.5.485 | ISC |
| es-module-lexer | 1.7.0 | MIT |
| esbuild | 0.25.12 | MIT |
| escalade | 3.2.0 | MIT |
| escape-string-regexp | 4.0.0 | MIT |
| eslint | 9.39.5 | MIT |
| eslint-plugin-react-hooks | 5.2.0 | MIT |
| eslint-plugin-react-refresh | 0.4.26 | MIT |
| eslint-scope | 8.4.0 | BSD-2-Clause |
| eslint-visitor-keys | 3.4.3 | Apache-2.0 |
| eslint-visitor-keys | 4.2.1 | Apache-2.0 |
| eslint-visitor-keys | 5.0.1 | Apache-2.0 |
| espree | 10.4.0 | BSD-2-Clause |
| esquery | 1.7.0 | BSD-3-Clause |
| esrecurse | 4.3.0 | BSD-2-Clause |
| estraverse | 5.3.0 | BSD-2-Clause |
| estree-walker | 3.0.3 | MIT |
| esutils | 2.0.3 | BSD-2-Clause |
| expect-type | 1.4.0 | Apache-2.0 |
| fast-deep-equal | 3.1.3 | MIT |
| fast-json-stable-stringify | 2.1.0 | MIT |
| fast-levenshtein | 2.0.6 | MIT |
| fdir | 6.5.0 | MIT |
| file-entry-cache | 8.0.0 | MIT |
| find-up | 5.0.0 | MIT |
| flat-cache | 4.0.1 | MIT |
| flatted | 3.4.4 | ISC |
| gensync | 1.0.0-beta.2 | MIT |
| glob-parent | 6.0.2 | ISC |
| globals | 14.0.0 | MIT |
| globals | 16.5.0 | MIT |
| has-flag | 4.0.0 | MIT |
| ignore | 5.3.2 | MIT |
| ignore | 7.0.14 | MIT |
| import-fresh | 3.3.1 | MIT |
| imurmurhash | 0.1.4 | MIT |
| is-extglob | 2.1.1 | MIT |
| is-glob | 4.0.3 | MIT |
| isexe | 2.0.0 | ISC |
| js-tokens | 9.0.1 | MIT |
| js-yaml | 4.3.2 | MIT |
| jsesc | 3.1.0 | MIT |
| json-buffer | 3.0.1 | MIT |
| json-schema-traverse | 0.4.1 | MIT |
| json-stable-stringify-without-jsonify | 1.0.1 | MIT |
| json5 | 2.2.3 | MIT |
| keyv | 4.5.4 | MIT |
| levn | 0.4.1 | MIT |
| locate-path | 6.0.0 | MIT |
| lodash.merge | 4.6.2 | MIT |
| loupe | 3.2.1 | MIT |
| lru-cache | 5.1.1 | ISC |
| magic-string | 0.30.21 | MIT |
| minimatch | 10.2.6 | BlueOak-1.0.0 |
| minimatch | 3.1.5 | ISC |
| ms | 2.1.3 | MIT |
| nanoid | 3.3.20 | MIT |
| natural-compare | 1.4.0 | MIT |
| node-releases | 2.0.64 | MIT |
| optionator | 0.9.4 | MIT |
| p-limit | 3.1.0 | MIT |
| p-locate | 5.0.0 | MIT |
| parent-module | 1.0.1 | MIT |
| path-exists | 4.0.0 | MIT |
| path-key | 3.1.1 | MIT |
| pathe | 2.0.3 | MIT |
| pathval | 2.0.1 | MIT |
| picocolors | 1.1.1 | ISC |
| picomatch | 4.0.7 | MIT |
| playwright | 1.65.1 | Apache-2.0 |
| playwright-core | 1.65.1 | Apache-2.0 |
| postcss | 8.5.33 | MIT |
| prelude-ls | 1.2.1 | MIT |
| punycode | 2.3.1 | MIT |
| react-refresh | 0.17.0 | MIT |
| resolve-from | 4.0.0 | MIT |
| rollup | 4.68.3 | MIT |
| semver | 6.3.2 | ISC |
| semver | 7.8.6 | ISC |
| shebang-command | 2.0.0 | MIT |
| shebang-regex | 3.0.0 | MIT |
| siginfo | 2.0.0 | ISC |
| source-map-js | 1.2.2 | BSD-3-Clause |
| stackback | 0.0.2 | MIT |
| std-env | 3.10.0 | MIT |
| strip-json-comments | 3.1.1 | MIT |
| strip-literal | 3.1.0 | MIT |
| supports-color | 7.2.0 | MIT |
| tinybench | 2.9.0 | MIT |
| tinyexec | 0.3.2 | MIT |
| tinyglobby | 0.2.17 | MIT |
| tinypool | 1.1.1 | MIT |
| tinyrainbow | 2.0.0 | MIT |
| tinyspy | 4.0.6 | MIT |
| topojson-client | 3.1.0 | ISC |
| ts-api-utils | 2.5.0 | MIT |
| type-check | 0.4.0 | MIT |
| typescript | 5.8.3 | Apache-2.0 |
| typescript-eslint | 8.72.2 | MIT |
| update-browserslist-db | 1.3.4 | MIT |
| uri-js | 4.4.1 | BSD-2-Clause |
| vite | 6.4.6 | MIT |
| vite-node | 3.2.4 | MIT |
| vitest | 3.2.7 | MIT |
| which | 2.0.2 | ISC |
| why-is-node-running | 2.3.0 | MIT |
| word-wrap | 1.2.5 | MIT |
| world-atlas | 2.0.2 | ISC |
| yallist | 3.1.1 | ISC |
| yocto-queue | 0.1.0 | MIT |

Generated by `node scripts/third-party.mjs` from the installed `node_modules` and `package-lock.json`.
