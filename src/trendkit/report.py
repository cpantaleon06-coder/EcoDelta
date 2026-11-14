"""One-series JSON-friendly trend summary for the web app."""

import math

import numpy as np
import pandas as pd

from .grid import MIN_VALID_FRACTION, MIN_YEARS, has_enough_data
from .mannkendall import DEFAULT_METHOD, mann_kendall, sens_slope
from .ols import ols_trend
from .seasonal import deseasonalize_monthly
from .timeutil import decimal_year, require_increasing


def _num(x):
    """JSON-safe float: NaN and infinity become None."""
    x = float(x)
    return x if math.isfinite(x) else None


def trend_report(y, dates, method=DEFAULT_METHOD, alpha=0.05, deseasonalize=None,
                 adjusted_pvalue=None, units=None):
    """Summarize the trend of one time series as a JSON-serializable dict.

    Pipeline:
      1. Optionally remove the monthly climatology (`deseasonalize_monthly`).
      2. Rate of change: Sen's slope, reported per decade, with its rank-based CI
         at level 1 - alpha built from the Var(S) of `method`.
      3. Significance: Mann-Kendall test with `method` (default: Yue-Wang AR(1)
         correction). `significant` is p < alpha, or adjusted_pvalue < alpha if given.
      4. Cross-check: OLS slope with t-test and AR(1)-adjusted CI.

    Minimum data requirement (same as `grid_trends`): at least MIN_YEARS = 10 years
    of valid data and at least MIN_VALID_FRACTION = 80% of time steps valid. Below
    that, statistics are still returned when computable, but `significant` is False
    and `verdict` is "insufficient data".

    Parameters
    ----------
    y : 1-D array-like of values; NaN = missing.
    dates : 1-D array-like of dates, strictly increasing, same length as y.
    method : Mann-Kendall variant (see `mann_kendall`).
    alpha : float, significance level and 1 - CI level.
    deseasonalize : bool, or None to deseasonalize only when the median time step
        is about one month (25 to 35 days).
    adjusted_pvalue : float, optional. A p-value already adjusted for multiple
        testing (for example an FDR q-value from `grid_trends`); used for `significant`.
    units : str, optional. Units of y, used to label the slope.

    Returns
    -------
    dict with JSON-safe values (None instead of NaN). Keys: n_valid, n_total,
    valid_fraction, period_start, period_end, deseasonalized, method, alpha,
    slope_per_decade, ci_low_per_decade, ci_high_per_decade, ci_level, slope_units,
    pvalue, adjusted_pvalue, kendall_tau, lag1_autocorrelation, ols, significant,
    verdict ("increasing", "decreasing", "no significant trend", "insufficient data"),
    warnings (list of plain-language strings).
    """
    y = np.asarray(y, dtype=float)
    idx = pd.DatetimeIndex(np.atleast_1d(dates))
    if y.ndim != 1 or len(idx) != y.size:
        raise ValueError(f"y must be 1-D with one value per date; got y {y.shape}, {len(idx)} dates")
    t = require_increasing(decimal_year(idx))

    step_days = float(np.median(np.diff(idx.values) / np.timedelta64(1, "D"))) if len(idx) > 1 else math.nan
    if deseasonalize is None:
        deseasonalize = 25 <= step_days <= 35
    constant = bool(np.any(~np.isnan(y))) and np.nanmin(y) == np.nanmax(y)  # before anomalies, which are all 0 under a year
    if deseasonalize:
        y, _ = deseasonalize_monthly(y, idx)

    n_valid = int(np.sum(~np.isnan(y)))
    enough = bool(has_enough_data(n_valid, t))
    mk = mann_kendall(y, method)
    ss = sens_slope(y, t, alpha, var_s=mk["var_s"])
    ols = ols_trend(y, t, alpha, ar1_adjust=True)
    p = mk["pvalue"] if adjusted_pvalue is None else adjusted_pvalue
    significant = enough and bool(p < alpha)
    slope = ss["slope"]
    if not enough:
        verdict = "insufficient data"
    elif significant:
        verdict = "increasing" if slope > 0 else "decreasing"
    else:
        verdict = "no significant trend"

    warnings = []
    valid_fraction = n_valid / y.size if y.size else 0.0
    years = n_valid * step_days / 365.25 if n_valid else 0.0
    if not years >= MIN_YEARS:  # also catches NaN from a single date
        warnings.append(f"Only about {np.nan_to_num(years):.1f} years of valid data; at least {MIN_YEARS} are needed "
                        "for a trend to be judged.")
    if valid_fraction < MIN_VALID_FRACTION:
        warnings.append(f"{100 * (1 - valid_fraction):.0f}% of values are missing (more than "
                        f"{100 * (1 - MIN_VALID_FRACTION):.0f}% allowed).")
    if constant:
        warnings.append("The series is constant, so it has no trend.")
    r1 = ols["resid_lag1_autocorr"]
    if r1 >= 0.5:
        warnings.append(f"Strong autocorrelation (lag-1 r = {r1:.2f}): neighbouring values are far from "
                        f"independent, so the series carries about {ols['n_eff']:.0f} independent values, "
                        f"not {n_valid}.")
    if r1 >= 0.3 and n_valid < 50:
        warnings.append("Short, autocorrelated series: in our simulations no test kept false alarms at 5% "
                        "here (8 to 13% at 25 points), so a 'significant' result is less certain than it looks.")
    if method == "original" and r1 >= 0.2:
        warnings.append("The plain Mann-Kendall test ignores autocorrelation, which is present here; "
                        "its p-value is too small.")
    if enough and (ols["pvalue"] < alpha) != (mk["pvalue"] < alpha):
        warnings.append("The OLS t-test and the Mann-Kendall test disagree on significance; the trend "
                        "may be non-linear or driven by outliers.")
    if deseasonalize and step_days > 35:
        warnings.append("The seasonal cycle was removed from data that are not monthly.")

    return {
        "n_valid": n_valid,
        "n_total": int(y.size),
        "valid_fraction": _num(valid_fraction),
        "period_start": idx[0].date().isoformat() if len(idx) else None,
        "period_end": idx[-1].date().isoformat() if len(idx) else None,
        "deseasonalized": bool(deseasonalize),
        "method": f"Sen's slope; Mann-Kendall test ({method})",
        "alpha": alpha,
        "slope_per_decade": _num(10 * slope),
        "ci_low_per_decade": _num(10 * ss["ci_low"]),
        "ci_high_per_decade": _num(10 * ss["ci_high"]),
        "ci_level": 1 - alpha,
        "slope_units": f"{units} per decade" if units else "per decade",
        "pvalue": _num(mk["pvalue"]),
        "adjusted_pvalue": None if adjusted_pvalue is None else _num(adjusted_pvalue),
        "kendall_tau": _num(mk["tau"]),
        "lag1_autocorrelation": _num(r1),
        "ols": {
            "slope_per_decade": _num(10 * ols["slope"]),
            "ci_low_per_decade": _num(10 * ols["ci_low"]),
            "ci_high_per_decade": _num(10 * ols["ci_high"]),
            "pvalue": _num(ols["pvalue"]),
            "ar1_adjusted": True,
        },
        "significant": significant,
        "verdict": verdict,
        "warnings": warnings,
    }
