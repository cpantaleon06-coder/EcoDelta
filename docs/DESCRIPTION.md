# EcoDelta: project description

NASA Space Apps Challenge 2026, "Be an Earth System Trend Detective".

Deployed site checked on 2026-11-15 at about 20:35 local time (https://eco-delta-wine.vercel.app, deployed
from commit `79cb6bb`, Vercel status "Deployment has completed"): `web_data/meta.json` has `source: real`,
`synthetic: false`, `build_date: 2026-11-15T13:59:19Z`, schema 1.3.0, `variables_included` evap, precip,
runoff_surface, soil_moisture_0_10cm, and `variables_missing` t2m. The air temperature files return HTTP 404.
The app code is the same as at commit `eb8228a`, where every claim about the app below was checked.

## In one paragraph

EcoDelta screens monthly NASA data for 21 regions (approximate latitude and longitude boxes, plus the
whole globe) and asks the same questions for every variable: did it change, in which direction, by how
much, and how sure can we be? Every result shows the trend per decade with its 95% confidence
interval, an evidence class kept separate from the size of the change, how much of the box has data,
and which data product it comes from. EcoDelta also checks its own output against other records, and
when a result disagrees and we cannot explain it, we hold it back instead of publishing it.

## What the app does (checked in the code at `eb8228a`)

- **Explore.** A world map of per-cell trends for one variable, and for each region a ranking of the
  variables, sortable by evidence or by magnitude. Map cells are marked significant only after a false
  discovery rate correction across all cells.
- **Region profile and detail.** For one region: the trend per decade, its 95% CI, the total change
  over the period, the evidence class, the share of the box with data, the source product, and the
  monthly series with its 12-month mean.
- **Guided questions.** The same results as four questions, one at a time: what changed, where, how
  much, and whether we can trust it.
- **Compare.** Tests whether two regions changed differently by fitting a trend to the difference of
  their two regional series, month by month, and shows that difference series. When the two boxes
  overlap, their averages share data and the result is a comparison of two overlapping areas, to be
  read with caution; the page says so next to the verdict.
- **About.** A provenance table: product, version, DOI where known, units, resolution, retrieval date.

Statistics: deseasonalized monthly anomalies, Sen's slope, Mann-Kendall test with Yue-Wang
autocorrelation correction, Benjamini-Hochberg false discovery rate. Methods are in
`trendkit/docs/METHODS.md`; the export format is in `ecodelta-engine/docs/OUTPUT_SCHEMA.md`.

## What is in the real export (built 2026-11-15T13:59:19Z)

Period 2001-01 to 2025-09 (297 months), 21 regions.

| Variable | Product | In the real export | Region results shown (limited) | Region results held back |
|---|---|---|---|---|
| Rain and snow (`precip`) | GPM IMERG V07 | Yes | 17 | 4 |
| Evaporation (`evap`) | GLDAS Noah 2.1 | Yes | 14 | 7 |
| Surface runoff (`runoff_surface`) | GLDAS Noah 2.1 | Yes | 11 | 10 |
| Soil moisture 0 to 10 cm (`soil_moisture_0_10cm`) | GLDAS Noah 2.1 | Yes | 5 | 16 |
| Air temperature near the ground (`t2m`) | MERRA-2 | **No, held back by the owner** | none | all |

No region result has the status "published"; see the quality gate below for why. The counts come from
`meta.quality_gate.counts`.

Other limits in the export:
- **Evidence is capped at "weak" where the fixed mask covers less than 30% of the box** (`LOW_COVERAGE =
  0.3` in `ecodelta-engine/src/ecodelta_engine/config.py`): evaporation in Central America and Caribbean,
  Global and Southeast Asia; surface runoff in Central America and Caribbean and Southeast Asia.
- **The trend maps are not gated.** The gate covers regional results only; the map still shows every
  grid cell, also inside regions whose regional result is held.
- **The app does not show the gate status yet.** The export marks every shown result "limited" and
  lists each held result with its reason, but the web app at `79cb6bb` does not display that label or
  the reasons. A held result is simply absent from the region's ranking.

## EcoDelta checks its own output, and holds back what it cannot defend

We ran three kinds of checks. They are different, and we say which is which.

**Pipeline checks (they test our code, not the science).**
- `python -m ecodelta_engine validate --source real` on the current export: 53 files with 0 schema
  errors and 0 consistency errors; 292 region pairs rebuilt from the exported series with 0
  mismatches; 161 numbers recomputed with trendkit with 0 mismatches.
- NASA POWER, Western Europe, air temperature (`ecodelta-engine/docs/VALIDATION.md`, section 2): our
  trend +0.528 °C per decade against +0.534 from POWER, about 1% apart, monthly anomalies correlated at
  0.99995. **This is not an independent check:** POWER itself is built on MERRA-2 (its API names
  `"sources": ["MERRA2"]`). It shows that our download, regridding, averaging and trend reproduce the
  source; it says nothing about whether MERRA-2 is right.

**Reference checks for the water variables (the quality gate, below).** Each region result is compared
with a second record on the same grid cells. None of these references is independent of the product,
as the engine itself records (`"independent": false` in `meta.quality_gate.references`):
- rain and snow against GPCP v3.3 (IMERG Final is calibrated to GPCP);
- evaporation, surface runoff and soil moisture against MERRA-2 land (`M2TMNXLND` EVLAND, RUNOFF, SFMC),
  another model with other forcing.

So no water variable is called validated anywhere in this project.

**Independent check for air temperature.**
- GISTEMP v4, global (`VALIDATION.md`, section 1): over the same 297 months with the same method, the
  MERRA-2 global trend is +0.163 °C per decade against +0.245 in GISTEMP v4, about one third lower. The
  confidence intervals overlap, but the gap is mostly in the polar bands, which matches a published
  evaluation of MERRA-2 (Simmons et al., 2016). GISTEMP blends sea surface and land air temperature, so
  it is not exactly the same quantity.
- The Sahel showed a significant cooling (−0.204 °C per decade) that we could not confirm or explain
  with any published number for this period.

**Decision.** Because of these two findings, the owner held back the **whole air temperature
variable** from the real export on 2026-11-14 (`hold:` in `ecodelta-engine/data/catalog/variables.yaml`).
It is listed as missing in the export, and the app shows only what is in the export. A tool that
publishes everything it computes would have shown a global warming trend one third too small and a
Sahel cooling nobody can confirm.

## Quality gate

Quality gate v1, approved by the owner on 2026-11-15 with G4 on (engine commit `a538514`, schema 1.3.0).
The full rule is in `ecodelta-engine/scripts/quality/gate.py` and is exported as
`meta.quality_gate.rule`. Each (variable, region) result gets one status: **published**, **limited** or
**held**. Held results are not exported as results; they are listed with their reason in
`meta.quality_gate.held`.

- **G0, pipeline.** A variable that fails any pipeline check (source units, 297 consecutive months, NaN
  pattern, raw against regridded, `validate --source real`) has all its results held.
- **G1, data.** A region whose fixed mask has 0 cells, or with valid data in fewer than 95% of the
  months, is held ("no data").
- **G2, reference trend check.** On the same cells and common months, the product and a fixed
  reference each get a trend (trendkit), and their difference D is tested (alpha 0.05). Each verdict is
  increasing or decreasing when p < 0.05, otherwise no clear trend.
  - verdicts differ and D is significant: **held** ("disagrees with the reference");
  - verdicts differ and D is not significant: **limited**;
  - verdicts agree and D is significant: **limited** (direction agrees, size differs);
  - verdicts agree and D is not significant: **published**.
  - Soil moisture has a reference in other units, so there is no D: verdicts differ, held; agree, limited.
  - No reference cells in the region: limited ("not checked against a reference").
- **G3, coverage of the check.** If the reference covers less than 50% of the product's cells in the
  region, the result is at most limited.
- **G4, independence.** If the reference is not independent of the product, the result is at most
  limited.
- **G5, air temperature.** Nothing is published for `t2m` without explicit owner approval, whatever
  the gate says.
- **G6, region comparisons.** A comparison of regions A and B gets the worse status of the two.

**Which variables pass.** No variable has a published result. All four water variables are capped at
limited by G4, because their references are not independent. Results are held where the product and
the reference disagree (G2) or where there is no data (G1, Antarctica for the three GLDAS variables,
which cover land from 60S to 90N only):

| Variable | Held regions (from `meta.quality_gate.held`) |
|---|---|
| `precip` | Antarctica, Central Africa, Mediterranean, Southern South America |
| `evap` | Amazon basin, Antarctica, Arctic (north of 66.5N), Eastern US, Middle East, Southern Africa, Southern South America |
| `runoff_surface` | Amazon basin, Antarctica, Australia, Global, Indian subcontinent, Mexico, Middle East, Siberia, Southern Africa, Southern South America |
| `soil_moisture_0_10cm` | Amazon basin, Antarctica, Arctic (north of 66.5N), Central Africa, Central America and Caribbean, East Africa, East China, Eastern US, Global, Indian subcontinent, Mediterranean, Mexico, Middle East, Sahel, Southern Africa, Western Europe |

`t2m` is not in the export at all: it stays held by the owner decision above (G5).

Limits of the gate (`VALIDATION.md`, section 7): there are 105 D tests at alpha 0.05, so about 5% flag
a difference by chance, which pushes towards holding; soil moisture is compared by verdict only; the
MERRA-2 land runoff includes throughflow and the GLDAS runoff does not; and the rule was written after
the air temperature and rain comparison tables had been seen, but before the GLDAS comparison was run.

## Limitations

- Regions are approximate boxes, not country or basin borders. A result for "Mexico" is a result for
  a box around Mexico, and the app tags every such region "approximate study area".
- A trend is not a cause. EcoDelta reports what changed, not why.
- 24.7 years is short for some variables; natural variability can hide or mimic a trend.
- Looking at many regions and variables raises the chance of false positives. The map uses a false
  discovery rate correction; the regional rankings are a screening tool, not proof.
- The flat map omits grid cells above about 85 degrees latitude (Web Mercator). Polar results are in
  the region list, ranking and detail panels.
- Accessibility: automated axe checks found 0 WCAG 2.x A and AA violations on the four main views (run
  on the demo data). No screen reader test was done.

## How EcoDelta differs from other tools

Other public projects work on the same theme. This is a factual comparison, not a ranking.

| | What it is | What EcoDelta adds |
|---|---|---|
| NASA Giovanni | A general NASA viewer for many data sets: maps, area-averaged time series and more | [TODO: owner fills this row after using Giovanni for the comparison in `VALIDATION.md`, section 3] |
| Trend Detective Lab | A project focused on Chile, with real data and extra validation | [TODO: link and a fact-checked line] |

What is distinctive in EcoDelta, all of it in the app at `79cb6bb` or in its export:
- Global screening: several variables and 21 regions in one tool, with one method.
- Evidence and magnitude shown separately, so a small but certain change and a large but uncertain one
  are not confused.
- Every result carries its uncertainty (95% CI), its coverage and its data source.
- A statistical comparison of two regions, with the difference series shown.
- A quality gate that compares every regional result with a reference record and holds back results
  that disagree, and a whole variable (air temperature) held back after an independent check.

## AI tools used

Claude and Claude Code (Anthropic) were used to help write code, tests, documentation and the
presentation. Decisions about what to publish or hold back, and the validation decisions, were made by
the team.

[TODO: owner confirms]

## Links

- Public app: [TODO: final link, public without login]
- Demo video: [TODO]
- Code: https://github.com/cpantaleon06-coder/EcoDelta
