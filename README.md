# EcoDelta

**Is the water cycle changing, and how sure can anyone be?**

EcoDelta is our entry for the NASA Space Apps Challenge 2026, challenge "Be an Earth System Trend Detective".
It screens monthly NASA data for 21 regions and the whole globe and answers four questions for every
variable: *what changed, where, by how much, and can we trust it?* Every result carries its trend per decade
with a 95% confidence interval, an evidence class kept separate from the size of the change, the share of the
region that has data, and the NASA product it comes from.

EcoDelta also checks its own output against independent records, and when a result disagrees with them and we
cannot explain why, we hold it back instead of publishing it.

| Link | |
|---|---|
| Live app | [TODO: final public link] |
| Demo (slides or video) | [TODO: demo link] |
| Source code | https://github.com/cpantaleon06-coder/EcoDelta |

## Why it exists

A trend you cannot trust is worse than no trend. Monthly climate data has memory: one warm month makes the next
one more likely to be warm. A standard trend test ignores that, and in our own simulation (`trendkit/docs/METHODS.md`,
2,000 trend-free series, 300 months) it flagged **32.8%** of series that had no real trend when the memory was
strong (the right answer is 5%). With the autocorrelation correction EcoDelta uses (Yue and Wang), the rate was
**5.4%**. Seasonal cycles, which hide slow change, and global averages, which hide regional change, add to the
problem.

## What it does

- **Explore.** A world map of per-cell trends for one variable, and for each region a ranking of the variables,
  sortable by evidence or by magnitude. A map cell is marked significant only after a false discovery rate
  correction across all cells.
- **Region profile.** Trend per decade, its 95% confidence interval, total change over the period, evidence class,
  share of the box with data, source product, and the monthly series with its 12-month mean.
- **Guided questions.** The same results as four questions, one at a time: what changed, where, how much, and
  whether we can trust it.
- **Compare.** Tests whether two regions changed differently by fitting a trend to the difference of their two
  regional series. When the two boxes overlap, their averages share data, and the page says so next to the verdict.
- **About.** A provenance table: product, version, DOI, units, resolution and retrieval date.

Regions are approximate latitude and longitude boxes, not country borders.

## The statistics

Deseasonalized monthly anomalies, Sen's slope, the Mann-Kendall test with Yue-Wang autocorrelation correction,
Benjamini-Hochberg false discovery rate control across map cells, and an OLS cross-check that has to agree.
Evidence (strong, moderate, weak, none, insufficient) is kept apart from magnitude, and evidence is capped at
"weak" when less than 30% of a region has data. Details: [trendkit/docs/METHODS.md](trendkit/docs/METHODS.md).

## How we used NASA data

Period: 2001-01 to 2025-09 (297 months), regridded to a 2 degree global grid. All products come from NASA GES DISC.

| Variable | Product | DOI |
|---|---|---|
| Rain and snow (`precip`) | GPM IMERG Final Monthly V07 (`GPM_3IMERGM`) | [10.5067/GPM/IMERG/3B-MONTH/07](https://doi.org/10.5067/GPM/IMERG/3B-MONTH/07) |
| Evaporation (`evap`) | GLDAS Noah Land Surface Model L4 monthly V2.1 (`GLDAS_NOAH025_M`) | [10.5067/SXAVCZFAQLNO](https://doi.org/10.5067/SXAVCZFAQLNO) |
| Surface runoff (`runoff_surface`) | GLDAS Noah 2.1 | [10.5067/SXAVCZFAQLNO](https://doi.org/10.5067/SXAVCZFAQLNO) |
| Soil moisture 0 to 10 cm (`soil_moisture_0_10cm`) | GLDAS Noah 2.1 | [10.5067/SXAVCZFAQLNO](https://doi.org/10.5067/SXAVCZFAQLNO) |
| Air temperature near the ground (`t2m`) | MERRA-2 `M2TMNXSLV` V5.12.4 | [10.5067/AP1B0BA5PD2K](https://doi.org/10.5067/AP1B0BA5PD2K) (**held back**, see below) |

Used only to check our own output, not redistributed: NASA GISTEMP v4 (https://data.giss.nasa.gov/gistemp/) and
the NASA POWER API (https://power.larc.nasa.gov/). Full citations are in `ecodelta-engine/web_data/meta.json`.

## What is real, and what EcoDelta held back

The real export (built 2026-11-15) has four water variables: rain and snow, evaporation, surface runoff and soil
moisture. They have passed pipeline checks only, not an independent check against another record. Please read their
results with that in mind.

**Air temperature (MERRA-2) is held back.** Our pipeline reproduces NASA POWER to about 1% (+0.528 against +0.534
degrees C per decade for Western Europe), but POWER is built on MERRA-2, so that check is not independent. Against
the independent GISTEMP v4 record, the MERRA-2 global trend for 2001 to 2024 is +0.169 against +0.252 degrees C per
decade, about one third lower, and almost all of the gap comes from the polar bands (Antarctica: -0.405 against
+0.084). This matches a published evaluation that found MERRA-2 colder than other datasets after about 2005
(Simmons et al., 2016). We also saw a cooling in the Sahel that we could not confirm. So we do not publish it.
Details and every number: [ecodelta-engine/docs/VALIDATION.md](ecodelta-engine/docs/VALIDATION.md).

Other limits shown in the app:
- Antarctica has no estimate for evaporation, surface runoff or soil moisture, because GLDAS covers land from 60S to 90N.
- Evidence is capped at "weak" where less than 30% of a region has data (land variables over mostly-ocean boxes).
- Overlapping boxes in Compare share data and should be read with caution.

## Repository layout

| Folder | What it is |
|---|---|
| [trendkit/](trendkit/) | Python statistics package: deseasonalizing, Sen's slope, Mann-Kendall with autocorrelation correction, FDR, regional means |
| [ecodelta-engine/](ecodelta-engine/) | Screens and ranks variables per region with trendkit and exports JSON for the web app (`web_data/`) |
| [web/](web/) | Static display-only website (Vite, React, TypeScript, MapLibre GL JS). It computes no statistics in the browser |
| [docs/](docs/) | Submission documents: description, pitch, demo plan |

The raw NASA download and regridding step lives outside this repository. The engine reads its processed files
from the folder set in `ECODELTA_DATA_DIR`, and the resulting export is committed in `ecodelta-engine/web_data/`.

## Run it

Requirements: Python 3.12 or newer, a current LTS version of Node.js.

```bash
# 1. Engine tests and a build on synthetic data (no NASA files needed)
cd ecodelta-engine
python -m venv .venv
.venv/bin/pip install -e ../trendkit
.venv/bin/pip install -e ".[dev]"
.venv/bin/python -m pytest
.venv/bin/python -m ecodelta_engine build --source fixture

# 2. Web app on the committed real export
cd ../web
npm install
npm run sync-data        # copies ../ecodelta-engine/web_data
npm run dev              # http://localhost:5173
```

`npm run build` refuses to build on synthetic data unless you set `ALLOW_FIXTURE=1`, so a demo build can never be
mistaken for real results. To rebuild the real export you need the processed NASA files and
`ECODELTA_DATA_DIR`; see [ecodelta-engine/docs/REPRODUCE.md](ecodelta-engine/docs/REPRODUCE.md).

## AI tools used

We used Super Intelligence (AI) tools in this project and want to be clear about where:

- **Claude and Claude Code (Anthropic)** helped write code (trendkit, the engine and the web app), tests and the
  documentation in this repository.
- Choices about what to publish and what to hold back (including holding back air temperature), the validation
  decisions, and the checks against independent records were made by the team.

No image, video or audio in this repository was generated by AI.

## Acknowledgements and third-party software

Data: NASA GES DISC (GPM IMERG, GLDAS, MERRA-2), NASA GISS (GISTEMP) and NASA POWER. EcoDelta is a project for the
NASA Space Apps Challenge. It is not an official NASA product, and it does not use NASA logos or mission identifiers.

Open source: NumPy, pandas, xarray, SciPy, netCDF4, PyYAML (engine); React, Vite, MapLibre GL JS, Recharts,
React Router, Poppins typeface via Fontsource, Natural Earth and `world-atlas` (web). Licenses:
[ecodelta-engine/THIRD_PARTY.md](ecodelta-engine/THIRD_PARTY.md) and [web/THIRD_PARTY.md](web/THIRD_PARTY.md).
