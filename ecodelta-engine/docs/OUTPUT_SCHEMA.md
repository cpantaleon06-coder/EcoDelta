# web_data output format (schema version 1.0.0)

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
```

Variable ids: `t2m`, `precip`, `evap`, `runoff_surface`, `soil_moisture_0_10cm` (always check
`meta.variables_included`; missing ones are in `meta.variables_missing`).
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
| `products` | data products: `name`, `short_name`, `version`, `doi`, `citation`, `variables`. Show these as credits. `"not found"` means we could not find the value. |
| `variables_included`, `variables_missing` | which variables are in this export |
| `limitations` | sentences to show on an "About the data" page |
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

## regions.json

`{"schema_version", "note", "regions": [{"id", "name", "phrase", "box"}]}`.
`box` is `[lat_min, lat_max, lon_min, lon_max]` in degrees (longitude -180 to 180). Boxes are
**approximate, not political borders** (show `note`). `phrase` is the name as used inside a sentence
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
| `n_valid` | number of valid months in that cell (0 = no data, for example ocean for land-only variables) |

Draw `slope` with a diverging color scale centered on 0; mark or hatch cells where `significant == 1`
(use `significant`, not `p`, on a map: `p` alone gives many false alarms over 16,200 cells). Cells with
`significant == null` have too little data; show them as "no data".

## screening/&lt;region_id&gt;.json

The ranked list for one region; small enough to load on every region click.

```json
{"schema_version": "1.0.0", "region_id": "sahel", "region_file": "regions/sahel.json",
 "ranking": [{"rank": 1, "variable": "precip", "name": "Rain and snow (precipitation)",
   "verdict": "increasing", "tier": 0, "significant": true, "pvalue": 1.363e-08,
   "effect_size": 0.782, "abs_effect_size": 0.782,
   "slope_per_decade": 0.212, "ci_per_decade": [0.1463, 0.2773], "public_unit": "mm/day",
   "sentence": "From January 2001 to September 2025, rain and snow (precipitation) in the Sahel changed by +0.212 mm/day per decade (95% confidence interval +0.146 to +0.277), which is statistically significant (p < 0.001). Over the whole 24.7-year period that is an increase of about 0.523 mm/day.",
   "cautions": []}, "..."]}
```

(Example from the synthetic fixture.) `rank` 1 is first. The order is: `tier` 0 (significant regional
trend), then 1 (not significant), then 2 (insufficient data); within a tier, smaller `pvalue` first; then
larger `abs_effect_size`. `effect_size` = trend per decade / standard deviation of the regional
anomalies (no unit; compares variables with different units). `verdict` is one of `increasing`,
`decreasing`, `no significant trend`, `insufficient data`. Show `cautions` (list of sentences, often
empty) right under the sentence.

## regions/&lt;region_id&gt;.json

```
{"schema_version", "region": {id, name, phrase, box}, "dates": ["2001-01", ...],
 "variables": {"<variable>": {"rank", "score", "answers", "sentence", "cautions", "report", "series"}}}
```

* `series`: `{"anomaly": [...], "running_mean_12": [...]}`, same length and order as `dates`, or `null`
  when the region has no valid cell for this variable. `anomaly` = regional monthly mean minus the
  average of that calendar month over the base period (so seasons are removed; 0 = normal for that
  month). `running_mean_12` = mean of the 12 months ending in that month (trailing); `null` for the first
  11 months. Plot `running_mean_12` as a line over light `anomaly` points. There are no annual means,
  because the last year is incomplete.
* `score`: `{tier, significant, pvalue, effect_size, abs_effect_size}` (see screening).
* `sentence`, `cautions`: plain-language text (same as in screening).
* `report`: trendkit's full regional trend report (null if no valid cell): `slope_per_decade`,
  `ci_low_per_decade`, `ci_high_per_decade`, `ci_level`, `pvalue`, `kendall_tau`, `lag1_autocorrelation`,
  `ols` (cross-check: `slope_per_decade`, CI, `pvalue`), `n_valid`, `n_total`, `valid_fraction`,
  `period_start`, `period_end`, `method`, `verdict`, `significant`, `warnings` (technical sentences).
* `answers`: the four questions of the challenge.

| Key | Contents |
|---|---|
| `what` | `variable`, `name`, `direction` (`increase`, `decrease`, `none detected`), `verdict` |
| `where` | `region`, `name`, `box`, `land_only`, `n_box_cells` (cells in the box), `n_valid_cells` (cells with enough data), `covered_fraction` (area share of the box with enough data, 0 to 1) |
| `how_much` | `period`, `period_years`, `units`, `public_unit`, `slope_per_decade`, `ci_per_decade` `[low, high]`, `total_change` (= slope x period_years / 10), `total_change_ci`, `ci_level` (0.95). Values are null when the verdict is `insufficient data`. |
| `data` | `n_valid_months`, `n_months`, `valid_fraction` of the regional series |
| `significance` | `verdict`, `significant`, `pvalue` (regional test), `alpha` (0.05), `test`, `qvalue` (always null: one test per region and variable), `cells_significant_after_fdr_fraction` (share of the region's tested cells significant on the FDR map), `explanation` (plain sentence), `warnings` (technical sentences from trendkit) |

## Wording rules for the web app

* Say "trend from 2001 to 2025", never "caused by".
* "No significant trend" is not "no change": the data cannot tell a small trend apart from natural ups
  and downs. Use the exported `explanation`.
* Statistically significant does not mean large or important.

## Checking a build

`python -m ecodelta_engine validate --source real` checks every file against `schema/`, checks internal
consistency (array lengths, `significant` vs `q`, screening vs region ranks) and recomputes a sample of
grid cells and regional reports directly with trendkit (golden test).
