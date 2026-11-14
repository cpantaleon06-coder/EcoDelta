# EcoDelta engine

The Python engine behind EcoDelta (NASA Space Apps Challenge 2026, "Be an Earth System Trend Detective").
For each region it screens a small catalog of NASA-derived Earth system variables, ranks them by how
credibly and how strongly they changed from 2001 to 2025, and writes plain-language answers to
*what changed, where, how much, and is it statistically significant?*

All statistics come from our package [trendkit](../trendkit). The engine exports precomputed JSON
to `web_data/`; the web app only displays it and never computes a trend.

## Install

Requires Python 3.12 or newer and the sibling folders `trendkit/` and (for real data) `nasa-data/`.

```bash
python -m venv .venv
.venv/bin/pip install -e ../trendkit
.venv/bin/pip install -e ".[dev]"
```

## Run

```bash
.venv/bin/python -m ecodelta_engine build --source fixture     # synthetic data -> web_data_fixture/
.venv/bin/python -m ecodelta_engine validate --source fixture
.venv/bin/python -m ecodelta_engine build --source real        # nasa-data -> web_data/
.venv/bin/python -m ecodelta_engine validate --source real
.venv/bin/python -m pytest
```

A build takes about 2 minutes (5 variables in parallel). It stops without exporting if a sanity check
fails (see `docs/ENGINE.md`). The data folder is set by one environment variable,
`ECODELTA_DATA_DIR` (default `../nasa-data`); it must contain `data/processed/manifest.json`, the NetCDF
files, and `docs/DATASETS.md`. If some variable files are missing, the build uses the rest and lists
the missing ones in `meta.json`.

## Folder layout

```
src/ecodelta_engine/
  config.py     every setting: paths, period, thresholds
  fixtures.py   synthetic data in the same format as nasa-data/data/processed
  load.py       read NetCDF files and check them against manifest.json
  catalog.py    join manifest.json + data/catalog/variables.yaml + DATASETS.md
  regions.py    region boxes, masks, area weights, coverage
  compute.py    trendkit grid trends, regional series and reports, sanity checks
  screen.py     ranking and the what / where / how much / significance answers
  narrate.py    rule-based sentences and caution lines
  export.py     write web_data/
  validate.py   JSON Schema, consistency and golden checks of an export
  cli.py        build / validate commands
data/catalog/   variables.yaml (plain-language definitions), regions.yaml (region boxes)
schema/         JSON Schema for every exported file
docs/           OUTPUT_SCHEMA.md (for the web developer), ENGINE.md, TRENDKIT_ISSUES.md
web_data_fixture/  export from synthetic data (do not show as real results)
web_data/          export from real data
```

See also `PROBLEMS.md` (what went wrong, what is not verified) and `THIRD_PARTY.md`.
