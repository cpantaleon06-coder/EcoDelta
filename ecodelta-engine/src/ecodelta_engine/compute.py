"""All statistics, through trendkit: per-cell trend grids and per-region series and reports.

Per variable (one process each, variables run in parallel):
  1. trendkit.grid_trends: deseasonalize every cell (monthly climatology over BASE_PERIOD),
     Sen's slope per decade with 95% CI, Mann-Kendall p (TREND_METHOD), BH-FDR q across cells.
  2. For each region: cells inside the box that pass trendkit's data rule (has_enough_data),
     trendkit.area_weighted_mean (cos-latitude weights, NaN aware), monthly anomalies
     (trendkit.deseasonalize_monthly), a trailing 12-month running mean for display,
     and trendkit.trend_report on the anomalies.
No annual means are produced: the last year (2025) has only 9 months.
"""

import os
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
from trendkit import area_weighted_mean, deseasonalize_monthly, grid_trends, trend_report
from trendkit.grid import has_enough_data
from trendkit.timeutil import decimal_year

from . import config
from .load import open_variable
from .regions import box_mask, coverage


def regional_report(series: np.ndarray, dates: np.ndarray, units: str) -> tuple[np.ndarray, dict]:
    """Anomalies and trendkit report of one regional series.

    Adapter: trend_report has no base_period argument (docs/TRENDKIT_ISSUES.md), so the anomalies
    are computed here with BASE_PERIOD and passed with deseasonalize=False. With the default
    BASE_PERIOD=None this equals trend_report(series, dates) exactly (golden test).
    """
    anomalies, _ = deseasonalize_monthly(series, dates, config.BASE_PERIOD)
    report = trend_report(anomalies, dates, method=config.TREND_METHOD, alpha=config.ALPHA,
                          deseasonalize=False, units=units)
    report["deseasonalized"] = True
    return anomalies, report


def running_mean(x: np.ndarray, n: int = config.RUNNING_MEAN_MONTHS) -> np.ndarray:
    """Trailing n-month mean (value at month t averages months t-n+1..t); NaN unless all n are valid."""
    return pd.Series(x).rolling(n, min_periods=n).mean().to_numpy()


def region_result(da: xr.DataArray, valid: xr.DataArray, grid: xr.Dataset, region: dict) -> dict:
    """Regional series, trend report and coverage for one variable and one region."""
    in_box = box_mask(region["box"], da.lat.values, da.lon.values)
    cov = coverage(in_box, valid)
    out = {"region": region["id"], **cov}
    if cov["n_valid_cells"] == 0:
        return out | {"series": None, "anomalies": None, "running_mean": None, "report": None,
                      "anomaly_sd": None, "effect_size": None, "cells_significant_fraction": None}
    dates = da.time.values
    series = area_weighted_mean(da, in_box & valid).values
    anomalies, report = regional_report(series, dates, da.attrs.get("units"))
    sd = float(np.nanstd(anomalies, ddof=1))
    slope = report["slope_per_decade"]
    tested = in_box & grid.pvalue.notnull()
    n_tested = int(tested.sum())
    return out | {
        "series": series,
        "anomalies": anomalies,
        "running_mean": running_mean(anomalies),
        "report": report,
        "anomaly_sd": sd,
        "effect_size": slope / sd if slope is not None and sd > 0 else None,
        "cells_significant_fraction": float((grid.significant & tested).sum()) / n_tested if n_tested else None,
    }


def compute_variable(root: Path, entry: dict, regions: list[dict], plausible_range=None) -> dict:
    """Grid trends and all regional results for one variable."""
    t0 = time.perf_counter()
    da = open_variable(root, entry)
    if plausible_range is not None:
        lo, hi = np.nanmin(da.values), np.nanmax(da.values)
        if lo < plausible_range[0] or hi > plausible_range[1]:
            raise ValueError(f"{entry['variable']}: values {lo:.3g}..{hi:.3g} {entry['units']} outside the "
                             f"plausible range {plausible_range}; check the units")
    grid = grid_trends(da, deseasonalize=True, method=config.TREND_METHOD, alpha=config.ALPHA,
                       q=config.FDR_Q, base_period=config.BASE_PERIOD)
    t_grid = time.perf_counter() - t0
    valid = xr.DataArray(has_enough_data(grid.n_valid.values, decimal_year(da.time.values)),
                         dims=("lat", "lon"), coords={"lat": da.lat, "lon": da.lon})
    regional = {r["id"]: region_result(da, valid, grid, r) for r in regions}
    return {
        "variable": entry["variable"],
        "units": entry["units"],
        "dates": da.time.values,
        "grid": grid,
        "regions": regional,
        "diagnostics": grid_diagnostics(da, grid),
        "timing_s": {"grid": round(t_grid, 1), "total": round(time.perf_counter() - t0, 1)},
    }


def grid_diagnostics(da: xr.DataArray, grid: xr.Dataset, n_sample: int = 200, seed: int = 0) -> dict:
    """Share of tested cells significant before (p < ALPHA) and after FDR, and, when more than half
    are significant after FDR, the median lag-1 autocorrelation of a fixed random sample of cells
    (from trendkit.trend_report) to help judge whether autocorrelation is underestimated."""
    tested = grid.pvalue.notnull()
    n = int(tested.sum())
    d = {
        "n_tested_cells": n,
        "fraction_p_below_alpha": round(float((grid.pvalue < config.ALPHA).sum()) / n, 4) if n else None,
        "fraction_significant_fdr": round(float(grid.significant.sum()) / n, 4) if n else None,
    }
    if n and d["fraction_significant_fdr"] > 0.5:
        idx = np.argwhere(tested.values)
        pick = idx[np.random.default_rng(seed).choice(len(idx), min(n_sample, len(idx)), replace=False)]
        r1 = [trend_report(da.values[:, i, j], da.time.values, method=config.TREND_METHOD)["lag1_autocorrelation"]
              for i, j in pick]
        d["sample_median_lag1_autocorrelation"] = round(float(np.nanmedian(np.array(r1, dtype=float))), 3)
    return d


def compute_all(root: Path, manifest: dict, variables: list[str], regions: list[dict],
                ranges: dict | None = None, workers: int | None = None) -> tuple[dict, dict]:
    """Run compute_variable for every variable in parallel. Returns (results, timing)."""
    t0 = time.perf_counter()
    workers = workers or min(len(variables), os.cpu_count() or 1)
    with ProcessPoolExecutor(workers) as pool:
        futures = {v: pool.submit(compute_variable, root, manifest[v], regions, (ranges or {}).get(v))
                   for v in variables}
        results = {v: f.result() for v, f in futures.items()}
    timing = {"wall_s": round(time.perf_counter() - t0, 1), "workers": workers,
              "per_variable_s": {v: r["timing_s"] for v, r in results.items()}}
    return results, timing


# Plausibility window for the global-mean 2 m temperature trend, in degC per decade. Our own loose
# bounds to catch sign or unit errors; they are not a published estimate.
T2M_GLOBAL_TREND_WINDOW = (0.0, 1.0)


def sanity_checks(results: dict) -> tuple[dict, list[str]]:
    """Numbers to report after every run, and blockers that must stop the export."""
    report, blockers = {}, []
    for var, res in results.items():
        g = res["regions"].get("global", {}).get("report")
        report[var] = {**res["diagnostics"],
                       "global_slope_per_decade": g and g["slope_per_decade"],
                       "global_ci_per_decade": g and [g["ci_low_per_decade"], g["ci_high_per_decade"]],
                       "global_pvalue": g and g["pvalue"],
                       "global_verdict": g and g["verdict"]}
        if not res["diagnostics"]["n_tested_cells"]:
            blockers.append(f"{var}: no grid cell passed the data requirement")
        if (res["diagnostics"]["fraction_significant_fdr"] or 0) > 0.5:
            report[var]["note"] = ("more than 50% of cells significant after FDR; check "
                                   "sample_median_lag1_autocorrelation and units before trusting it")
    if "t2m" in results:
        s = report["t2m"]["global_slope_per_decade"]
        lo, hi = T2M_GLOBAL_TREND_WINDOW
        if s is None or not lo < s < hi:
            blockers.append(f"t2m: global-mean trend {s} degC/decade is outside the plausibility window {lo}..{hi}")
    return report, blockers
