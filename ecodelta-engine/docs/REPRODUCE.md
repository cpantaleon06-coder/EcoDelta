# Reproducing web_data/ from NASA data

What is in git and what is not:

| In git | Not in git (and why) |
|---|---|
| `ecodelta-engine/web_data/` (real export, about 1 MB once published, so the site works without NASA credentials; none published yet) | NetCDF files: raw subsets are never stored; `data/interim/` (one file per product-month) and `data/processed/` (one 14 MB file per variable) are rebuilt by the steps below |
| `ecodelta-engine/` code, schemas, catalog, docs; `trendkit/` | `~/.netrc` (your Earthdata credentials) |
| `nasa-data/` scripts and docs: **not yet in git on 2026-11-14**; see `PROBLEMS.md` | `build/` (fixture data, cached NASA POWER responses), `.venv/`, `logs/` |

Tested with Python 3.14.4 on Linux.

## 1. Earthdata credentials (once)

1. Create an Earthdata Login account at https://urs.earthdata.nasa.gov and authorize the application
   "NASA GESDISC DATA ARCHIVE" (Applications > Authorized Apps).
2. Create `~/.netrc` with your own values and make it private. Never commit this file.

```bash
printf 'machine urs.earthdata.nasa.gov login YOUR_USERNAME password YOUR_PASSWORD\n' > ~/.netrc
```

```bash
chmod 600 ~/.netrc
```

## 2. Download and regrid (nasa-data)

Pinned versions: earthaccess 0.19.0, xarray 2026.9.0, netCDF4 1.7.5.1.post1, h5netcdf 1.8.3,
numpy 2.5.4, scipy 1.18.1, pandas 3.1.1, requests 2.34.2.

```bash
cd nasa-data && python3 -m venv .venv && .venv/bin/pip install earthaccess==0.19.0 xarray==2026.9.0 netCDF4==1.7.5.1.post1 h5netcdf==1.8.3 numpy==2.5.4 scipy==1.18.1 pandas==3.1.1 requests==2.34.2
```

```bash
.venv/bin/python -I scripts/build_coarse_grid.py selftest
```

```bash
.venv/bin/python -I scripts/build_coarse_grid.py run
```

```bash
.venv/bin/python -I scripts/build_coarse_grid.py assemble
```

- **`run`.** Fetches only the needed variables for each month through GES DISC OPeNDAP, converts the
  units, regrids to 2 x 2 degrees, and writes `data/interim/<product>/<YYYY-MM>.nc`. It is resumable:
  rerun it after any interruption and finished months are skipped. A 401 or 403 response stops it with
  a hint; it does not retry those.
- **`assemble`.** Writes `data/processed/<variable>.nc` and `manifest.json` for every product whose 297
  months are all present. It reads the provenance (collection id, version, DOI, source units, native
  and temporal resolution) from CMR and from one real source file, so these depend on what NASA serves
  on the day you run it.
- **Background runs.** The download takes hours, so run it detached from your terminal, for example
  with `setsid nohup ... &`. A run inside a tool session died when that session ended (see `PROBLEMS.md`).

Measured download times on 2026-11-14, from `logs/build.log`, per product-month (fetch + regrid +
write). They depend on the GES DISC server load at that time.

| Product | Months measured | Mean | Median | Total |
|---|---|---|---|---|
| MERRA-2 (`T2M`, 0.65 MB per month) | 297 of 297 | 7.8 s | 4.4 s | 38.7 min |
| IMERG (`precipitation`, 7.2 MB per month) | 52 of 297 so far | 13.0 s | 5.4 s | rose to 47-122 s per month after 19:26 |
| GLDAS (3 variables, 2.45 MB per month) | not started | | | |

## 3. Engine: build and validate web_data

Pinned versions: numpy 2.5.4, pandas 3.1.1, xarray 2026.9.0, scipy 1.18.1, netCDF4 1.7.5.1.post1,
PyYAML 6.0.3, jsonschema 4.26.0, pytest 9.2.0; trendkit from `../trendkit` (0.1.0).

```bash
cd ecodelta-engine && python3 -m venv .venv && .venv/bin/pip install -e ../trendkit && .venv/bin/pip install -e ".[dev]" numpy==2.5.4 pandas==3.1.1 xarray==2026.9.0 scipy==1.18.1 netCDF4==1.7.5.1.post1 PyYAML==6.0.3 jsonschema==4.26.0 pytest==9.2.0
```

```bash
export ECODELTA_DATA_DIR=/path/to/nasa-data
```

```bash
.venv/bin/python -m ecodelta_engine build --source real --allow-missing
```

```bash
.venv/bin/python -m ecodelta_engine validate --source real
```

- **Quality gate.** A real build needs `data/catalog/quality_gate.json` with a status for every
  (variable, region); the build stops otherwise. To regenerate it: fetch the references with
  `nasa-data/scripts/fetch_reference.py` (GLDAS Tair, GPCP, MERRA-2 land) and the GISTEMP gridded files
  into `nasa-data/data/reference/gistemp/`, run the comparison scripts in `scripts/quality/` (commands
  in `docs/VALIDATION.md` sections 4 to 7), then `.venv/bin/python -I scripts/quality/gate.py --write`.
- **Holds.** A variable whose `data/catalog/variables.yaml` entry has `hold:` is never exported in the
  real build, even when its data is complete. `t2m` is held since 2026-11-14 (see `docs/VALIDATION.md`).
  With every complete variable held, the build exports nothing and exits with code 1.
- **`--allow-missing`.** Builds only the variables that are in `manifest.json`, i.e. complete. The
  catalog then lists only those, and `meta.variables_missing` names the rest. Without the flag, the
  build stops when any variable described in `data/catalog/variables.yaml` has no real data.
- **Build time.** `t2m` alone took 52.6 s and 55.5 s (two runs). With all five variables, the fixture
  build takes about 2 minutes.
- **Validation.** `validate` checks the JSON Schemas and internal consistency, and recomputes sample
  grid cells and regional reports with trendkit directly.
- **POWER check.** `.venv/bin/python scripts/validate_power.py western_europe` repeats the NASA POWER
  comparison in `docs/VALIDATION.md`.

## 4. Check that you got the same result

`meta.data.manifest_sha256` names the exact `manifest.json` used. Different retrieval dates give a
different manifest hash, but the same data should give the same numbers.

After a rebuild, compare with the committed export. `meta.json` always differs, because it contains
`build_date` and `timing`:

```bash
git status --short ecodelta-engine/web_data
```

Only `meta.json` should be listed. `catalog.json` is also listed when the manifest hash, the retrieval
dates or the engine commit differ. That is expected: those fields record provenance, not data. Any
other file listed means the numbers changed.

Verified on 2026-11-14: two consecutive builds of the real `t2m` export from the same processed files
gave 45 of 46 files byte-identical. `meta.json` differed only in `build_date` and `timing`. These were
two local builds compared with each other: nothing was committed yet, so this is not yet a check
against a committed copy.
