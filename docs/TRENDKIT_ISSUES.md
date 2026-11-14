# trendkit issues found while building the engine

Nothing here is forked: each item is worked around in the engine and listed for the trendkit owners.

| # | Issue | Effect | Workaround in ecodelta_engine |
|---|---|---|---|
| 1 | `trend_report` has no `base_period` argument, while `grid_trends` and `deseasonalize_monthly` do. | A regional report cannot use a custom climatology base period. | `compute.regional_report` deseasonalizes with `deseasonalize_monthly(..., base_period)` and calls `trend_report(..., deseasonalize=False)`, then sets `deseasonalized=True`. With the default base period (full record) the result equals `trend_report(series, dates)`; a test checks this. Side effect: trend_report's "constant series" warning is evaluated on anomalies instead of raw values. |
| 2 | `has_enough_data` is not exported from `trendkit/__init__.py`. | Minor; we import it from `trendkit.grid`. | None needed. |
| 3 | `grid_trends` is single-process and memory-bandwidth heavy (pairwise arrays of about chunk x n_time^2). Alone: 52.6 s for 90 x 180 x 300 (trendkit's benchmark). Five variables in parallel processes: the full t2m grid took 120.8 s on the fixture run. | Parallel variables slow each other down. | Variables run in parallel processes; total wall time is still about 2 minutes (see docs/ENGINE.md). |
