"""All statistics, through trendkit: per-cell trend grids and per-region series and reports.

Per variable (one process each, variables run in parallel):
  1. trendkit.grid_trends: deseasonalize every cell (monthly climatology over BASE_PERIOD),
     Sen's slope per decade with 95% CI, Mann-Kendall p (TREND_METHOD), BH-FDR q across cells.
  2. For each region: trendkit.fixed_mask_mean over the cells of the box valid in at least 95% of
     the months, the same cells every month (cos-latitude weights; a month is missing when more
     than 5% of the mask's weight is missing; config.FIXED_MASK), monthly anomalies
     (trendkit.deseasonalize_monthly), a trailing 12-month running mean for display,
     and trendkit.trend_report on the anomalies.
  3. For each pair of regions (compare_regions): the trend test on D(t) = A(t) - B(t), the difference of
     the two regions' anomalies on their common months.
No annual means are produced: the last year (2025) has only 9 months.
"""

import os
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
from trendkit import area_weighted_mean, deseasonalize_monthly, fdr_bh, fixed_mask_mean, grid_trends, trend_report
from trendkit.grid import has_enough_data
from trendkit.timeutil import decimal_year

from . import config
from .load import open_variable
from .regions import area_weights, box_mask, coverage
from .screen import evidence


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
    fixed_series, fm = fixed_mask_mean(da, in_box, config.FIXED_MASK_MIN_VALID, config.FIXED_MASK_MAX_MISSING_WEIGHT) \
        if in_box.any() else (None, {"n_cells": 0, "region_area_fraction": 0.0, "n_valid": 0,
                                     "n_total": da.sizes["time"], "weight_share_min": None, "weight_share_max": None})
    fixed = {"n_cells": fm["n_cells"], "covered_fraction": round(fm["region_area_fraction"], 4),
             "n_valid_months": fm["n_valid"], "n_months": fm["n_total"],
             "weight_share_min": fm["weight_share_min"], "weight_share_max": fm["weight_share_max"]}
    out = {"region": region["id"], **cov, "fixed_mask": fixed}
    tested = in_box & grid.pvalue.notnull()
    n_tested = int(tested.sum())
    sig = grid.significant & tested
    map_cells = {"n_tested": n_tested, "n_significant": int(sig.sum()),
                 "n_significant_increasing": int((sig & (grid.slope > 0)).sum()),
                 "n_significant_decreasing": int((sig & (grid.slope < 0)).sum()),
                 "share_significant": float(sig.sum()) / n_tested if n_tested else None}
    if (fixed["n_cells"] if config.FIXED_MASK else cov["n_valid_cells"]) == 0:
        return out | {"series": None, "anomalies": None, "running_mean": None, "report": None,
                      "anomaly_sd": None, "effect_size": None, "total_change": None, "residual_sd": None,
                      "standardized_change": None, "cells_significant_fraction": map_cells["share_significant"],
                      "map_cells": map_cells}
    dates = da.time.values
    series = fixed_series.values if config.FIXED_MASK else area_weighted_mean(da, in_box & valid).values
    anomalies, report = regional_report(series, dates, da.attrs.get("units"))
    sd = float(np.nanstd(anomalies, ddof=1))
    slope = report["slope_per_decade"]
    t = decimal_year(dates)
    has_slope = slope is not None and report["verdict"] != "insufficient data"
    # magnitude: total change over the period / SD of the anomalies around the Sen trend line
    residual_sd = float(np.nanstd(anomalies - (slope / 10 * t if has_slope else 0), ddof=1))
    total = slope * (t[-1] - t[0]) / 10 if has_slope else None
    return out | {
        "series": series,
        "anomalies": anomalies,
        "running_mean": running_mean(anomalies),
        "report": report,
        "anomaly_sd": sd,
        "effect_size": slope / sd if slope is not None and sd > 0 else None,
        "total_change": total,
        "residual_sd": residual_sd,
        "standardized_change": total / residual_sd if has_slope and residual_sd > 0 else None,
        "cells_significant_fraction": map_cells["share_significant"],
        "map_cells": map_cells,
    }


COMPARE_METHOD = ("D(t) = A(t) - B(t), the difference of the two regions' deseasonalized fixed-mask monthly means "
                  "on the months where both have a value; Sen's slope with 95% CI and Mann-Kendall (same autocorrelation "
                  "handling as the regional trends) on D. 'trends differ' when p < alpha. P-values of the two regions are "
                  "never compared, and overlapping confidence intervals are not used as a test. When the boxes overlap, the "
                  "shared cells do not cancel in D: each mean is divided by its own total area weight (W_A, W_B), so a shared "
                  "cell i enters D with weight w_i (1/W_A - 1/W_B), which is zero only when W_A = W_B.")
COMPARE_NOTE = ("Each p-value is valid for one comparison chosen in advance. Looking through many pairs and picking those "
                "that differ raises the chance of false positives: about 1 in 20 pairs with no real difference will show "
                "'trends differ'. When two boxes overlap, their averages share data and the two results are not "
                "independent. Shared cells do not fully cancel in the difference, because each average is divided by its "
                "own area, so read such a result as a comparison of two overlapping areas.")
Q_NOTE = ("q_across_pairs: Benjamini-Hochberg q-value across all region pairs of this variable, for scanning many pairs "
          "at once. Approximate: the pairs share regions and are not independent.")


def compare_pair(a: np.ndarray, b: np.ndarray, dates: np.ndarray) -> dict:
    """Trend test on D = a - b (deseasonalized series; NaN where either is missing)."""
    d = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    rep = trend_report(d, dates, method=config.TREND_METHOD, alpha=config.ALPHA, deseasonalize=False)
    ok = rep["verdict"] != "insufficient data"
    return {"verdict": ("trends differ" if rep["significant"] else "no evidence that trends differ") if ok
            else "insufficient data",
            "difference_slope_per_decade": rep["slope_per_decade"] if ok else None,
            "difference_ci_per_decade": [rep["ci_low_per_decade"], rep["ci_high_per_decade"]] if ok else None,
            "pvalue": rep["pvalue"] if ok else None,
            "n_common_months": int(np.isfinite(d).sum())}


def box_overlap(box_a, box_b, lat: np.ndarray, lon: np.ndarray) -> float:
    """Share of the smaller box's area inside the other box (2 degree cells by center)."""
    a, b = box_mask(box_a, lat, lon), box_mask(box_b, lat, lon)
    w = xr.DataArray(area_weights(lat), dims="lat", coords={"lat": lat})
    return float((w * (a & b)).sum()) / min(float((w * a).sum()), float((w * b).sum()))


def own_trend(rr: dict) -> dict:
    rep = rr["report"]
    ok = rep is not None and rep["verdict"] != "insufficient data"
    return {"slope_per_decade": rep["slope_per_decade"] if ok else None,
            "ci_per_decade": [rep["ci_low_per_decade"], rep["ci_high_per_decade"]] if ok else None,
            "pvalue": rep["pvalue"] if ok else None, "evidence_class": evidence(rr)["class"]}


def compare_regions(res: dict, regions: list[dict]) -> list[dict]:
    """Every pair of regions (in list order) for one variable, plus a BH q-value across the pairs."""
    lat, lon = res["grid"].lat.values, res["grid"].lon.values
    pairs = []
    for i, ra in enumerate(regions):
        for rb in regions[i + 1:]:
            A, B = res["regions"][ra["id"]], res["regions"][rb["id"]]
            ov = box_overlap(ra["box"], rb["box"], lat, lon)
            test = compare_pair(A["anomalies"], B["anomalies"], res["dates"]) \
                if A["anomalies"] is not None and B["anomalies"] is not None else \
                {"verdict": "insufficient data", "difference_slope_per_decade": None,
                 "difference_ci_per_decade": None, "pvalue": None, "n_common_months": 0}
            pairs.append({"region_a": ra["id"], "region_b": rb["id"], **test,
                          "trend_a": own_trend(A), "trend_b": own_trend(B),
                          "overlap_fraction": round(ov, 4), "independent": ov == 0})
    q, _ = fdr_bh([np.nan if e["pvalue"] is None else e["pvalue"] for e in pairs], config.ALPHA)
    for e, qq in zip(pairs, q):
        e["q_across_pairs"] = None if np.isnan(qq) else float(qq)
    return pairs


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
