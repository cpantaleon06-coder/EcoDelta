# How the EcoDelta engine works

Every number below comes from a real run on the date shown. Results on **real** data are not here yet:
the download was still running when this was written (see PROBLEMS.md).

Pipeline: `load` (check files against manifest.json) -> `catalog` (join plain-language text, manifest and
DATASETS.md) -> `compute` (trendkit statistics, sanity checks) -> `screen` + `narrate` (ranking, answers,
sentences) -> `export` (web_data/) -> `validate` (schemas, consistency, golden recomputation).
Run it with `python -m ecodelta_engine build --source fixture|real`; nothing else changes between the two.

## Compute (step 4)

All statistics come from trendkit; the engine only arranges inputs and outputs.

For every variable:
1. **Per-cell trends**: `trendkit.grid_trends` removes each cell's monthly climatology (base period: the
   full record, 2001-01 to 2025-09; set `BASE_PERIOD` in `config.py` to change it), then computes Sen's slope
   per decade with a 95% confidence interval, a Mann-Kendall p-value with the Yue-Wang AR(1) correction
   (the method trendkit's METHODS.md recommends), and a Benjamini-Hochberg q-value across all tested cells of
   that variable (target false discovery rate 5%).
2. **Data rule** (trendkit's own): a cell or regional series is judged only with at least 10 years of
   valid months and at least 80% of months valid. Cells failing it are left out of maps, regional means
   and FDR; a region with no passing cell gets the verdict "insufficient data".
3. **Per region** (schema 1.2.0): a fixed mask, the cells inside the region box with data in at least 95%
   of the months, is averaged with cos(latitude) weights, using the same cells every month
   (`trendkit.fixed_mask_mean`; on this 2 degree grid cos(latitude) is exactly proportional to cell
   area). A month is missing when more than 5% of the mask's weight has no data. This prevents spurious
   trends from cells entering or leaving the record (proof in trendkit docs/METHODS.md section 7). The regional series is turned into monthly anomalies
   (`trendkit.deseasonalize_monthly`) and summarized by `trendkit.trend_report`.
4. **Display series**: monthly anomalies and a trailing 12-month running mean (the mean of the 12 months
   ending in that month; empty until 12 valid months are available). No annual means are published,
   because the last year (2025) has only 9 months.
5. **Evidence and magnitude** (schema 1.2.0): an evidence class (strong, moderate, weak, none,
   insufficient data) and a magnitude block (slope, total change, standardized change = total change /
   SD of the detrended anomalies); see trendkit docs/METHODS.md section 7b. The 1.1.0 effect size
   (slope / SD of the anomalies) is still exported.
6. **Region comparison** (schema 1.2.0): for each pair of regions, the trend test on the difference of
   their anomaly series (`compute.compare_regions`, `compare/<variable>.json`).

Stops before export (blockers): any value outside the loose `plausible_range` in `variables.yaml`
(catches unit mistakes), a variable with no testable cell, or a global-mean 2 m temperature trend outside
0 to 1 degC per decade (our own plausibility window, not a published value).

### Timing

Variables run in parallel processes (one per variable). Fixture run, 2026-11-14, AMD Ryzen 5 3600
(6 cores, 12 threads), all 5 variables x 21 regions: **122.7 s wall time**. t2m (16,200 cells) took
120.8 s for its grid; the land-only variables (7,345 cells) about 79 s each. trendkit's own benchmark
gives 52.6 s for one full grid alone, so the parallel processes slow each other down
(memory bandwidth), but the total stays near 2 minutes.

### Sanity checks on fixture data (2026-11-14)

The fixture has known planted trends (`fixtures.PLANTED`), so these numbers test the pipeline, not the Earth.

| Variable | Tested cells | p < 0.05 | Significant after FDR | Global-mean trend per decade (95% CI) |
|---|---|---|---|---|
| t2m | 16,200 | 55.6% | 46.8% | +0.272 degC (0.258 to 0.286); planted about +0.275 |
| precip | 14,400 | 6.9% | 0.9% | +0.004 mm/day (-0.008 to 0.015), not significant |
| evap | 7,345 | 7.2% | 1.2% | +0.001 mm/day, not significant |
| runoff_surface (pure noise) | 7,345 | 5.4% | 0.0% | -0.000 mm/day, not significant |
| soil_moisture_0_10cm | 7,345 | 9.5% | 2.0% | -0.032 kg/m2, not significant |

The pure-noise variable shows 5.4% of cells with p < 0.05 and none after FDR, as expected. Real-data
results will be added after the real run.

## Screening, ranking and sentences (step 5)

**Ranking** (`screen.py`, schema 1.2.0). Two orderings are exported per region. `by_evidence`: evidence
class, then smaller p-value, then larger |standardized change|, then variable id; `rank` is the position
here. `by_magnitude`: larger |standardized change|, then stronger evidence, then smaller p-value, then
variable id. Before 1.2.0 the order was tier, p-value, effect size, so effect size almost never mattered;
the 1.1.0 `score` is still exported.

**Answers.** Each region and variable gets `what` (variable, direction, verdict), `where` (region, box,
cells in the box, valid cells, area-weighted coverage), `how_much` (trend per decade with 95% CI, total
change over the period with CI = trend x 24.67 years / 10, units), `data` (valid months) and `significance`
(p-value, verdict, plain explanation, share of the region's cells significant after FDR, trendkit
warnings). The regional test is a single test per variable and region, so `qvalue` is null; FDR applies
to the grid cells.

**Sentences** (`narrate.py`, fixed templates, no language model). Always the period and the 95% CI; a
non-significant result says "no statistically significant trend" and "does not mean nothing changed";
no causal words. Caution lines only for: a CI wider than the trend itself, more than 5% of months
missing, less than 30% of the region's area covered (or fewer than 5 cells).

**Measured false-positive rate of the regional verdict** (2026-11-14, 400 trend-free series of 297
months, seasonal cycle plus AR(1) noise, seed 7): 5.2% at phi = 0, 6.2% at phi = 0.4, 5.8% at phi = 0.6.
With 400 series the sampling error is about +/-1.1 percentage points, so these agree with trendkit's own
Monte Carlo (METHODS.md section 5). On the fixture, one of the pure-noise regional tests came out
significant (evapotranspiration in the Sahel, p = 0.042), as expected at this rate.

## Export and validation (step 6)

`export.py` writes the files described in `docs/OUTPUT_SCHEMA.md` into a temporary folder and swaps it in
place, so a failed build never leaves a half-written `web_data/`. Every number is rounded to 4 significant
digits; keys are sorted. A build with any blocker exports nothing.

Fixture build, 2026-11-14: **50 files, 3.93 MB** (budget 25 MB). The five grid files are the largest
(0.60 to 0.71 MB each); the 21 region files and 21 screening files are small. Build wall time 123.3 s.

`python -m ecodelta_engine validate --source fixture` (about 5 s):
* JSON Schema: 50 files, 0 errors;
* consistency (array lengths, `significant` agrees with `q <= 0.05`, screening order = region ranks): 0 errors;
* golden test: 220 exported numbers recomputed by calling trendkit directly on the NetCDF files
  (5 random tested cells per variable: slope, CI, p; regions global, Sahel, Arctic, Mediterranean for every
  variable: slope, CI, p, verdict and the first 24 anomalies), 0 mismatches.

To check that validation is not toothless, we changed three values in a copy of the export (a regional
slope by +0.001, a sentence into a number, one `significant` flag); each was reported (golden, schema,
consistency), and validate exited with status 1.

**Determinism** (2026-11-14): two fixture builds in a row gave byte-identical files except `meta.json`,
which differs only in `build_date` and `timing` (second build: 119.3 s wall time).
