# EcoDelta: project description

NASA Space Apps Challenge 2026, "Be an Earth System Trend Detective".

Written 2026-11-15 from the repository at commit `eb8228a` and the real export built
2026-11-15T13:09:31Z. Claims about the app were checked against the code and a local build of that
commit. The deployed site has not been checked yet: [TODO: open the public link in a private window
and confirm the data badge and each claim below].

## In one paragraph

EcoDelta screens monthly NASA data for 21 regions (approximate latitude and longitude boxes, plus the
whole globe) and asks the same questions for every variable: did it change, in which direction, by how
much, and how sure can we be? Every result shows the trend per decade with its 95% confidence
interval, an evidence class kept separate from the size of the change, how much of the box has data,
and which data product it comes from. EcoDelta also checks its own output against independent records,
and when a result disagrees and we cannot explain it, we hold it back instead of publishing it.

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

## What is real in the export (2026-11-15T13:09:31Z)

Period 2001-01 to 2025-09 (297 months), 21 regions.

| Variable | Product | In the real export | Checks done |
|---|---|---|---|
| Rain and snow (`precip`) | GPM IMERG V07 | Yes | Pipeline checks only |
| Evaporation (`evap`) | GLDAS Noah 2.1 | Yes | Pipeline checks only |
| Surface runoff (`runoff_surface`) | GLDAS Noah 2.1 | Yes | Pipeline checks only |
| Soil moisture 0 to 10 cm (`soil_moisture_0_10cm`) | GLDAS Noah 2.1 | Yes | Pipeline checks only |
| Air temperature near the ground (`t2m`) | MERRA-2 | **No, held back** | Pipeline check and independent check; see below |

Results that are not shown, or shown with a lower evidence class, and why:

- **Antarctica has no estimate for evaporation, surface runoff or soil moisture.** GLDAS covers land
  from 60S to 90N only, so the box has no data.
- **Evidence is capped at "weak" where less than 30% of the box has data** (land variables over
  mostly-ocean boxes): evaporation in Central America and Caribbean, Global and Southeast Asia; surface
  runoff in Central America and Caribbean and Southeast Asia; soil moisture in Central America and
  Caribbean and Global.

None of the four water variables has been compared with an independent record yet. They are not
called validated anywhere in this project. [TODO: run an independent check for at least one water
variable, or keep this sentence.]

## EcoDelta checks its own output, and held back what it could not defend

We ran two kinds of checks. They are different, and we say which is which.

**Pipeline checks (they test our code, not the science).**
- `python -m ecodelta_engine validate --source real` on the current export: 53 files with 0 schema
  errors and 0 consistency errors; 780 region pairs rebuilt from the exported series with 0
  mismatches; 248 numbers recomputed with trendkit with 0 mismatches.
- NASA POWER, Western Europe, air temperature (`ecodelta-engine/docs/VALIDATION.md`, section 2): our
  trend +0.528 °C per decade against +0.534 from POWER, about 1% apart, monthly anomalies correlated at
  0.99995. **This is not an independent check:** POWER itself is built on MERRA-2 (its API names
  `"sources": ["MERRA2"]`). It shows that our download, regridding, averaging and trend reproduce the
  source; it says nothing about whether MERRA-2 is right.

**Independent check (it tests the data against another record).**
- GISTEMP v4, global, air temperature (`VALIDATION.md`, section 1): over the same 297 months with the
  same method, the MERRA-2 global trend is +0.163 °C per decade against +0.245 in GISTEMP v4, about one
  third lower. The confidence intervals overlap, but the gap is mostly in the polar bands, which
  matches a published evaluation of MERRA-2 (Simmons et al., 2016). GISTEMP blends sea surface and
  land air temperature, so it is not exactly the same quantity.
- The Sahel showed a significant cooling (−0.204 °C per decade) that we could not confirm or explain
  with any published number for this period.

**Decision.** Because of these two findings, the owner held back the **whole air temperature
variable** from the real export on 2026-11-14 (`hold:` in `ecodelta-engine/data/catalog/variables.yaml`).
It is listed as missing in the export, and the app shows only what is in the export. A tool that
publishes everything it computes would have shown a global warming trend one third too small and a
Sahel cooling nobody can confirm.

**Quality gate.** Today the gate is that hold: a written owner decision, recorded with its reason in
the catalog, applied by the engine at export time. [TODO: write the final quality gate rule here,
for example which independent check a variable must pass and with what tolerance, and say which
variables pass it.]

## Limitations

- Regions are approximate boxes, not country or basin borders. A result for "Mexico" is a result for
  a box around Mexico, and the app tags every such region "approximate study area".
- A trend is not a cause. EcoDelta reports what changed, not why.
- 24.7 years is short for some variables; natural variability can hide or mimic a trend.
- Looking at many regions and variables raises the chance of false positives. The map uses a false
  discovery rate correction; the regional rankings are a screening tool, not proof.
- The flat map omits grid cells above about 85 degrees latitude (Web Mercator). Polar results are in
  the region list, ranking and detail panels.
- Accessibility: automated axe checks found 0 WCAG 2.x A and AA violations on the four main views. No
  screen reader test was done.

## How EcoDelta differs from other tools

Other public projects work on the same theme. This is a factual comparison, not a ranking.

| | What it is | What EcoDelta adds |
|---|---|---|
| NASA Giovanni | A general NASA viewer for many data sets: maps, area-averaged time series and more | [TODO: owner fills this row after using Giovanni for the comparison in `VALIDATION.md`, section 3] |
| Trend Detective Lab | A project focused on Chile, with real data and extra validation | [TODO: link and a fact-checked line] |

What is distinctive in EcoDelta, all of it in the app at `eb8228a`:
- Global screening: several variables and 21 regions in one tool, with one method.
- Evidence and magnitude shown separately, so a small but certain change and a large but uncertain one
  are not confused.
- Every result carries its uncertainty (95% CI), its coverage and its data source.
- A statistical comparison of two regions, with the difference series shown.
- A result that failed an independent check was withheld rather than shown.

## AI tools used

- Claude Code (Anthropic), for code, tests and documentation.
- [TODO: owner confirms this list and adds any other AI tools used.]

## Links

- Public app: [TODO: final link, public without login]
- Demo video: [TODO]
- Code: https://github.com/cpantaleon06-coder/EcoDelta
