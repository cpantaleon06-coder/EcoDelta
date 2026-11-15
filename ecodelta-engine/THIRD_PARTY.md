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

The processed NetCDF files are made by the data session (`nasa-data`) from NASA GES DISC products.
Product names, versions, DOIs and citations are exported in `web_data/meta.json`, read from
`nasa-data/docs/DATASETS.md`. That file copies the CMR `CollectionCitations` fields. Since schema 1.1.0,
each variable in `web_data/catalog.json` also carries a `provenance` block (collection id, version,
DOI, source units, resolution, retrieval dates, processing and statistics), read from the data build's
`manifest.json`.

No real export is published yet (2026-11-14). `t2m` has complete data but is held back by the owner
(see `docs/VALIDATION.md`). Its source, recorded for when it is released:

| Variable | Product | Collection id (CMR) | Version | DOI | Citation (from CMR metadata) |
|---|---|---|---|---|---|
| `t2m` | MERRA-2 tavgM_2d_slv_Nx (M2TMNXSLV) | C1276812859-GES_DISC | 5.12.4 | 10.5067/AP1B0BA5PD2K | Global Modeling and Assimilation Office (GMAO) (2015), MERRA-2 tavgM_2d_slv_Nx: 2d,Monthly mean,Time-Averaged,Single-Level,Assimilation,Single-Level Diagnostics V5.12.4, Greenbelt, MD, USA, Goddard Earth Sciences Data and Information Services Center (GES DISC), doi:10.5067/AP1B0BA5PD2K |

IMERG (GPM_3IMERGM v07) and GLDAS (GLDAS_NOAH025_M v2.1) will be listed here once their data is
complete; their DOIs and citations are already in `nasa-data/docs/DATASETS.md`.

Datasets used **only for validation**. They are not redistributed, and none of their numbers appear
in `web_data/` (see `docs/VALIDATION.md`):

- GISTEMP Team, 2026: GISS Surface Temperature Analysis (GISTEMP), version 4. NASA Goddard Institute for
  Space Studies. Dataset accessed 2026-11-14 at https://data.giss.nasa.gov/gistemp/. Lenssen, N., et al.,
  2024: A GISTEMPv4 observational uncertainty ensemble. J. Geophys. Res. Atmos., 129, e2023JD040179,
  doi:10.1029/2023JD040179.
- NASA POWER Monthly and Annual API v2.10.0 (https://power.larc.nasa.gov/), accessed 2026-11-14. Its API
  header names its source as MERRA-2.
