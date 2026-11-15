# web_data output format (schema version 1.2.0)

Changes in 1.2.0 (additive; 1.1.0 readers keep working):
* Regional means use a **fixed spatial mask** (the same cells every month); its diagnostics are in
  `answers.where.fixed_mask`, and the rule is in `meta.methods.regional_mean_rule`.
* **Evidence and magnitude are separate.** Every region-variable result has an `evidence` class
  (`strong`, `moderate`, `weak`, `none`, `insufficient data`) and a `magnitude` block (trend per decade,
  total change, and a unitless `standardized_change`). Screening files carry two orderings,
  `by_evidence` and `by_magnitude`; `rank` now follows `by_evidence`. Definitions are in
  `meta.methods.evidence_classes`, `meta.methods.magnitude` and `meta.methods.orderings`.
* **Maps and spatial dependence.** `grids/` files add a per-cell `evidence` class index. Region files add
  `map_cells` (counts of tested and FDR-significant cells in the box), and screening entries add
  `cells_significant_fraction`. `meta.methods.fdr.spatial_dependence` and `meta.limitations` state that
  neighbouring cells are correlated, so Benjamini-Hochberg holds only approximately.
* **Region comparison.** New files `compare/<variable>.json` test, for every pair of regions, whether
  their trends differ (see below).
* **Region labels.** Every region has `kind` (`"approximate_box"`) and `display_note` (show it next to
  the region name).

Changes in 1.1.0 (additive; 1.0.0 readers keep working): `meta.data.manifest_sha256` and a
`provenance` block on every `catalog.json` variable.

Everything the web app needs is precomputed JSON. **The browser never computes a trend**: it only
reads, filters and draws these files. Machine-readable JSON Schemas live in `schema/`; this page
explains them. `web_data/` holds real results, `web_data_fixture/` holds results from **synthetic**
data (same format; `meta.synthetic` is `true`; never present those numbers as real).

```
web_data/
  meta.json                  build info, period, grid, methods, data products, limitations
  catalog.json               the variables, with plain-language text
  regions.json               the region list (id, name, box)
  grids/<variable>.json      per-cell trend map of one variable
  regions/<region_id>.json   everything about one region: series, reports, answers, sentences, ranks
  screening/<region_id>.json the ranked list of variables for one region (small; load this first)
  compare/<variable>.json    do the trends of two regions differ? one entry per pair of regions
```

Variable ids: `t2m`, `precip`, `evap`, `runoff_surface`, `soil_moisture_0_10cm` (always check
`meta.variables_included`; missing ones are in `meta.variables_missing`, which also lists variables
the owner held back from the real export).
Region ids: see `regions.json` (21, starting with `global`).

## General rules

* **Numbers** are rounded to 4 significant digits. **`null`** means "no value" (ocean cell of a land-only
  variable, too little data, or the first 11 months of a running mean). Never treat `null` as 0.
* **Trends** are "per decade" in the variable's own `units` (`units` is the file unit such as `degC`,
  `public_unit` is the label to show such as `°C`).
* **Months** are strings `"YYYY-MM"`; each monthly value is the mean of that month.
* Keys are sorted alphabetically; the order of keys has no meaning. The order of arrays does.
* Always show the period (`meta.period`, for example 2001-01 to 2025-09) next to any trend, and the 95%
  confidence interval next to any trend value.

## meta.json

| Key | Meaning |
|---|---|
| `schema_version` | version of this format; a change in the first number breaks compatibility |
| `build_date` | UTC time of the build |
| `source`, `synthetic` | `"real"` or `"fixture"`; `synthetic: true` means fake test data |
| `engine`, `trendkit` | `version`, git `commit` (null if the repository had no commit) and `uncommitted_changes` |
| `period` | `start`, `end` (`YYYY-MM`), `n_months`, `years` (length from first to last month) |
| `grid` | `resolution_deg` (2), `lat` and `lon` axes as `{first, last, step, n}` (cell centers) |
| `methods` | how everything was computed (text and parameters): trend estimator, test, `autocorrelation_handling`, `alpha`, `fdr`, climatology base period, data requirement, regional mean, display series, `ranking` (definition of the order), `rounding` |
| `methods.fdr` | `{method, q, applies_to, spatial_dependence}`; `spatial_dependence` is the plain limitation sentence about correlated neighbouring cells (show it with the maps) |
| `methods.evidence_classes` | thresholds of the evidence classes (see "Evidence and magnitude" below) |
| `methods.magnitude` | definition and limits of `standardized_change` |
| `methods.orderings` | `{by_evidence, by_magnitude}`: definition and tie-breaks of the two orderings |
| `methods.regional_mean_rule` | `{mode, min_valid_fraction, max_missing_weight}`. `mode` is `"fixed_mask"`: a regional mean uses only the cells of the box that are valid in at least `min_valid_fraction` (0.95) of the months, and the same cells every month. A month is `null` (missing) when cells holding more than `max_missing_weight` (0.05) of the mask's area weight have no value that month; otherwise it is the area-weighted mean of the mask cells that have a value. |
| `products` | data products: `name`, `short_name`, `version`, `doi`, `citation`, `variables`. Show these as credits. `"not found"` means we could not find the value. |
| `variables_included`, `variables_missing` | which variables are in this export |
| `limitations` | sentences to show on an "About the data" page |
| `data` | `manifest_sha256`: SHA-256 of the data build's `manifest.json`, identifying the exact processed files used (null only if unknown) |
| `timing`, `sanity_checks` | build diagnostics (not for display) |

## catalog.json

`{"schema_version", "variables": [ ... ]}`, one object per variable:

| Key | Meaning |
|---|---|
| `id` | variable id |
| `name` | short plain-language name ("Air temperature near the ground") |
| `definition` | one sentence a high school student understands |
| `increase_means` | one sentence: what an increase means |
| `units`, `public_unit` | file unit and the label to show |
| `land_only` | true if the variable has values only over land (60S to 90N) |
| `caveats` | list of sentences (data source type, resolution, coverage) |
| `long_name`, `period` | technical name and `[start, end]` |
| `product` | `name`, `short_name`, `version`, `source_variable`, `doi`, `citation`, `unit_conversion` |
| `provenance` | where every number comes from (below); show it on a "Data sources" or "How this was made" panel |

`provenance` keys. Data values are copied from the data build's `manifest.json`, which reads them from NASA's
CMR catalog and from a real source file; `null` means the value could not be retrieved (all data values are
null in the synthetic fixture).

| Key | Meaning |
|---|---|
| `product_short_name`, `collection_id`, `version`, `doi` | NASA product short name, CMR collection concept id (for example `C1276812859-GES_DISC`), product version, DOI |
| `source_variable`, `source_units` | variable name and units in the NASA file |
| `units`, `displayed_units` | units of the exported numbers, and the label shown (same numbers) |
| `native_resolution` | `{lon_deg, lat_deg, n_lon, n_lat, lat_range, from, cmr_gridded_resolution}` of the source grid |
| `grid` | the 2 x 2 degree grid used here (`resolution_deg`, `shape`, cell centers) |
| `temporal_resolution` | `{per_file, example_granule_range, from}`: one value per calendar month |
| `period` | `[start, end]` as `YYYY-MM` |
| `retrieved` | `{data_first, data_last, metadata, from}`: dates the monthly files and the metadata were fetched |
| `processing_steps` | list of `{step, detail}`: unit conversion, then regridding |
| `statistics` | `trendkit_version`, `deseasonalizing`, `climatology_base_period`, `trend_estimator` (Sen), `significance_test` (Mann-Kendall), `autocorrelation_handling` and `autocorrelation_note` (Yue-Wang), `alpha`, `ci_level`, `fdr` (Benjamini-Hochberg, `q`), `data_requirement`, `regional_mean` |
| `engine_commit`, `engine_uncommitted_changes` | git commit of the engine that made the export |
| `manifest_sha256` | same as `meta.data.manifest_sha256` |

## regions.json

`{"schema_version", "note", "regions": [{"id", "name", "phrase", "box", "kind", "display_note"}]}`.
`box` is `[lat_min, lat_max, lon_min, lon_max]` in degrees (longitude -180 to 180). Boxes are
**approximate, not political borders** (show `note`). `kind` is `"approximate_box"` for every region
(1.2.0); `display_note` is the short label to show next to the region name or on the map outline:
"approximate study area, not a political border". The same two keys are in the `region` object of
`regions/<region_id>.json`. `phrase` is the name as used inside a sentence
("the Sahel"). A grid cell belongs to a region when its center is inside the box.

## grids/&lt;variable&gt;.json

A trend map. Each array has `lat.n * lon.n` = 16,200 entries in **row-major order**:
`index = i_lat * lon.n + i_lon`, with `lat = lat.first + i_lat * lat.step` (south to north) and
`lon = lon.first + i_lon * lon.step` (west to east). Each value describes a 2 x 2 degree cell centered there.

| Key | Meaning |
|---|---|
| `slope` | trend per decade, in `slope_units` (Sen's slope of the deseasonalized monthly series) |
| `ci_low`, `ci_high` | 95% confidence interval of the slope |
| `p` | Mann-Kendall p-value of that cell alone |
| `q` | false-discovery-rate adjusted p-value (Benjamini-Hochberg across all tested cells of this variable) |
| `significant` | `1` if `q <= 0.05`, `0` if tested but not significant, `null` if not tested |
| `evidence` | evidence class of the cell as an index into `evidence_classes` (`["strong", "moderate", "weak", "none"]`), using `q` in place of `p` (see "Evidence and magnitude"); `null` if not tested |
| `evidence_classes` | the list the `evidence` index points into |
| `n_valid` | number of valid months in that cell (0 = no data, for example ocean for land-only variables) |

Draw `slope` with a diverging color scale centered on 0; mark or hatch cells where `significant == 1`
(use `significant`, not `p`, on a map: `p` alone gives many false alarms over 16,200 cells). Cells with
`significant == null` have too little data; show them as "no data".

**Spatial dependence (show this next to any significance map).** Neighbouring cells are correlated.
Benjamini-Hochberg control of the false discovery rate is proven for independent or positively dependent
tests, so on these maps it holds only approximately: a single map can have more or fewer false discoveries
than 5%. trendkit's Monte Carlo test measured a false discovery proportion of 0.059 +/- 0.007 (mean of
40 synthetic maps, seeds 100-139; target 0.05; trendkit docs/METHODS.md section 6). Those synthetic maps
have autocorrelation in time but independent noise from cell to cell, so they do **not** include the
spatial correlation of real maps, which can push a single real map further from 5%. The exact sentence is
in `meta.methods.fdr.spatial_dependence`.

## Evidence and magnitude

How sure we are that there is a trend (**evidence**) and how big it is (**magnitude**) are different
questions. Show both; never use one as a stand-in for the other. A strong trend can be small, and a
large estimate can have no evidence behind it.

**Evidence class** of a regional result. `p` is the regional Mann-Kendall p-value and "CI excludes 0" means
the whole 95% confidence interval of the slope is above 0 or below 0.

| Class | Rule |
|---|---|
| `strong` | p < 0.01 and CI excludes 0 |
| `moderate` | p < 0.05 and CI excludes 0 (not strong) |
| `weak` | p < 0.10 (not moderate or strong), or p < 0.05 with a CI that includes 0 |
| `none` | everything else with enough data |
| `insufficient data` | no regional report or verdict `insufficient data` (fewer than 10 years or 80% of months) |

Coverage rule: when the fixed mask covers less than 30% of the box (`where.fixed_mask.covered_fraction <
0.3`), `strong` and `moderate` become `weak` and `capped_by_coverage` is `true`. On the maps the same rule
uses the cell's FDR `q` instead of `p` (see `grids/`).

**Magnitude**: `slope_per_decade` and `total_change` (= slope x `period_years` / 10) in the variable's
`units`, and `standardized_change` = `total_change` / `residual_sd`, where `residual_sd` is the standard
deviation of the deseasonalized monthly regional series after removing the Sen trend line. It has no unit,
so variables with different units can be compared inside one region. It answers: "how many typical monthly
swings did the trend add up to over the period?". Limits: it is not a measure of importance or impact; it
is smaller for noisy variables (precipitation) and larger for big regions (averaging lowers the SD), so
compare variables within a region, not regions with each other; it uses monthly values, so it is smaller
than the same measure on annual means; it grows with the length of the period. Never show a percent of the
mean for temperature in °C (0 °C is not "no temperature").

**Orderings** (in `screening/`):

* `by_evidence`: class `strong`, `moderate`, `weak`, `none`, `insufficient data`; ties: smaller `pvalue`
  first, then larger `|standardized_change|`, then variable id (alphabetical). `rank` is the position here.
* `by_magnitude`: larger `|standardized_change|` first; results without one (`insufficient data`) last;
  ties: stronger evidence class, then smaller `pvalue`, then variable id. Show the evidence class next to
  every entry of this ordering: a large estimate with evidence `none` may be noise.

## screening/&lt;region_id&gt;.json

The ranked list for one region; small enough to load on every region click.

```json
{"schema_version": "1.1.0", "region_id": "sahel", "region_file": "regions/sahel.json",
 "ranking": [{"rank": 1, "variable": "precip", "name": "Rain and snow (precipitation)",
   "verdict": "increasing", "tier": 0, "significant": true, "pvalue": 1.363e-08,
   "effect_size": 0.782, "abs_effect_size": 0.782,
   "slope_per_decade": 0.212, "ci_per_decade": [0.1463, 0.2773], "public_unit": "mm/day",
   "sentence": "From January 2001 to September 2025, rain and snow (precipitation) in the Sahel changed by +0.212 mm/day per decade (95% confidence interval +0.146 to +0.277), which is statistically significant (p < 0.001). Over the whole 24.7-year period that is an increase of about 0.523 mm/day.",
   "cautions": []}, "..."]}
```

(Example from the synthetic fixture; 1.2.0 files also have the keys below.) `rank` 1 is first; since 1.2.0
`ranking` and `rank` follow `by_evidence` (see "Evidence and magnitude"). Added in 1.2.0:

* top level: `by_evidence` and `by_magnitude`, lists of variable ids in the two orders;
* per entry: `evidence_class`, `total_change` (units as `public_unit`), `standardized_change`, `rank_by_magnitude`,
  `cells_significant_fraction` (share of the region's tested map cells that are significant after FDR).

`tier` (0 = significant regional trend, 1 = not significant, 2 = insufficient data), `effect_size`
(trend per decade / standard deviation of the regional anomalies, not detrended) and `abs_effect_size`
are kept for 1.1.0 readers. `verdict` is one of `increasing`,
`decreasing`, `no significant trend`, `insufficient data`. Show `cautions` (list of sentences, often
empty) right under the sentence.

## regions/&lt;region_id&gt;.json

```
{"schema_version", "region": {id, name, phrase, box}, "dates": ["2001-01", ...],
 "variables": {"<variable>": {"rank", "rank_by_magnitude", "score", "evidence", "magnitude", "answers",
                              "sentence", "cautions", "report", "series"}}}
```

* `series`: `{"anomaly": [...], "running_mean_12": [...]}`, same length and order as `dates`, or `null`
  when the region's fixed mask has no cell for this variable. `anomaly` = regional monthly mean minus the
  average of that calendar month over the base period (so seasons are removed; 0 = normal for that
  month). `running_mean_12` = mean of the 12 months ending in that month (trailing); `null` for the first
  11 months. Plot `running_mean_12` as a line over light `anomaly` points. There are no annual means,
  because the last year is incomplete.
* `score`: `{tier, significant, pvalue, effect_size, abs_effect_size}` (see screening).
* `evidence`: `{class, ci_excludes_zero, capped_by_coverage}` (see "Evidence and magnitude").
* `map_cells`: `{n_tested, n_significant, n_significant_increasing, n_significant_decreasing,
  share_significant}`: grid cells of the box tested on the map, and how many are significant after FDR
  (`share_significant` = `n_significant / n_tested`, null when nothing was tested; same value as
  `answers.significance.cells_significant_after_fdr_fraction`).
* `magnitude`: `{slope_per_decade, total_change, units, residual_sd, standardized_change}`, null values when
  there is no regional report. `rank_by_magnitude`: position in `by_magnitude`.
* `sentence`, `cautions`: plain-language text (same as in screening).
* `report`: trendkit's full regional trend report (null if no valid cell): `slope_per_decade`,
  `ci_low_per_decade`, `ci_high_per_decade`, `ci_level`, `pvalue`, `kendall_tau`, `lag1_autocorrelation`,
  `ols` (cross-check: `slope_per_decade`, CI, `pvalue`), `n_valid`, `n_total`, `valid_fraction`,
  `period_start`, `period_end`, `method`, `verdict`, `significant`, `warnings` (technical sentences).
* `answers`: the four questions of the challenge.

| Key | Contents |
|---|---|
| `what` | `variable`, `name`, `direction` (`increase`, `decrease`, `none detected`), `verdict` |
| `where` | `region`, `name`, `box`, `land_only`, `n_box_cells` (cells in the box), `n_valid_cells` (cells that pass the map's data requirement, 10 years and 80% of months), `covered_fraction` (area share of the box covered by those cells, 0 to 1), `fixed_mask` (below) |
| `where.fixed_mask` | the cells the regional mean is made of (see `meta.methods.regional_mean_rule`): `n_cells` (cells in the fixed mask), `covered_fraction` (area share of the box covered by the mask, 0 to 1; **this is the part of the region the result describes**), `n_valid_months` and `n_months` (months with a regional value, out of all months), `weight_share_min` and `weight_share_max` (lowest and highest share of the mask's area weight with data in any month, 0 to 1; `null` when the mask is empty) |
| `how_much` | `period`, `period_years`, `units`, `public_unit`, `slope_per_decade`, `ci_per_decade` `[low, high]`, `total_change` (= slope x period_years / 10), `total_change_ci`, `ci_level` (0.95). Values are null when the verdict is `insufficient data`. |
| `data` | `n_valid_months`, `n_months`, `valid_fraction` of the regional series |
| `significance` | `verdict`, `significant`, `pvalue` (regional test), `alpha` (0.05), `test`, `qvalue` (always null: one test per region and variable), `cells_significant_after_fdr_fraction` (share of the region's tested cells significant on the FDR map), `explanation` (plain sentence), `warnings` (technical sentences from trendkit) |

## compare/&lt;variable&gt;.json

Answers "is the trend in region A different from the trend in region B?" for one variable, for every pair
of regions (21 regions: 210 pairs).

```
{"schema_version", "variable", "units", "public_unit", "period", "method", "note", "q_note",
 "pairs": [{"region_a", "region_b", "verdict", "difference_slope_per_decade", "difference_ci_per_decade",
            "pvalue", "q_across_pairs", "n_common_months", "trend_a", "trend_b",
            "overlap_fraction", "independent"}, ...]}
```

**Method.** `D(t) = A(t) - B(t)`, where A and B are the deseasonalized monthly regional series (the
`series.anomaly` of the two region files, fixed-mask means) on the months where both have a value. The
same trend test as everywhere else runs on `D`: Sen's slope with 95% CI, Mann-Kendall with the Yue-Wang
correction. A trend in `D` means the two regional trends differ. Testing `D` takes into account that the
two regions move together from month to month. Comparing the two p-values, or checking whether the two
confidence intervals overlap, does not, and **is never used**.

| Key | Meaning |
|---|---|
| `region_a`, `region_b` | region ids; pairs appear once, in the order of `regions.json` (`region_a` first) |
| `verdict` | `"trends differ"` (p < 0.05), `"no evidence that trends differ"`, or `"insufficient data"` (a region without a series, or `D` fails the data requirement) |
| `difference_slope_per_decade`, `difference_ci_per_decade` | trend of `D` = trend of A minus trend of B, per decade, with the 95% CI `[low, high]`, in `units` |
| `pvalue` | Mann-Kendall p-value of `D` (a **single** planned comparison) |
| `q_across_pairs` | Benjamini-Hochberg q-value across all pairs of this variable. Use it only when scanning many pairs at once (see `q_note`). |
| `n_common_months` | months where both regions have a value |
| `trend_a`, `trend_b` | each region's own trend: `{slope_per_decade, ci_per_decade, pvalue, evidence_class}` (null values when the region has no report) |
| `overlap_fraction` | share of the smaller box's area that lies inside the other box (cells by center, 0 to 1) |
| `independent` | `false` when the boxes overlap (`overlap_fraction > 0`). The shared cells then cancel in `D`, so the test compares only the parts that do not overlap, and the two regional results are not independent. |

Values are null when the verdict is `insufficient data`. Show `note` with every comparison. Each
p-value is valid for **one** comparison chosen in advance. Looking through many pairs and picking the
ones that differ raises the chance of false positives (about 1 in 20 pairs with no real difference will
show `"trends differ"`). `q_across_pairs` corrects for scanning all pairs of one variable, but only
approximately, because the pairs share regions and are not independent.

## Wording rules for the web app

* Say "trend from 2001 to 2025", never "caused by".
* "No significant trend" is not "no change": the data cannot tell a small trend apart from natural ups
  and downs. Use the exported `explanation`.
* Statistically significant does not mean large or important.

## Checking a build

`python -m ecodelta_engine validate --source real` checks every file against `schema/`, checks internal
consistency (array lengths, `significant` vs `q`, screening vs region ranks) and recomputes a sample of
grid cells and regional reports directly with trendkit (golden test).
