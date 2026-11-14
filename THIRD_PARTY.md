# Third-party code

**No third-party source code is copied into this repository.** All code under `src/`, `tests/` and
`schema/` was written for EcoDelta.

## Dependencies (installed with pip, not vendored)

License values as reported by each package's installed metadata on 2026-11-14.

| Package | Version | License (from package metadata) |
|---|---|---|
| trendkit | 0.1.0 | our own sibling project (`../trendkit`) |
| numpy | 2.5.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |
| pandas | 3.1.1 | BSD-3-Clause |
| xarray | 2026.9.0 | Apache-2.0 |
| scipy | 1.18.1 | BSD License (classifier) |
| netCDF4 | 1.7.5.1.post1 | MIT |
| PyYAML | 6.0.3 | MIT |
| jsonschema | 4.26.0 | MIT |
| pytest (tests only) | 9.2.0 | MIT |

## Data

The processed NetCDF files are made by the data session (`nasa-data`) from NASA GES DISC products;
product names, versions, DOIs and citations are exported in `web_data/meta.json` (read from
`nasa-data/docs/DATASETS.md`).
