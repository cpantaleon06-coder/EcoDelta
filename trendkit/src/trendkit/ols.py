"""Ordinary least squares trend with t-test and confidence interval."""

import numpy as np
from scipy import stats


def ols_trend(y, t, alpha=0.05, ar1_adjust=False):
    """Linear trend y = a + b t fitted by ordinary least squares, with a t-test on b.

    Formulas (sums over valid points only):
        b      = sum((t - tbar)(y - ybar)) / Sxx,   Sxx = sum((t - tbar)^2)
        SE(b)  = sqrt(SSR / (df * Sxx)),            SSR = sum(residual^2), df = n_eff - 2
        t_stat = b / SE(b);  p = 2 * P(T_df > |t_stat|)          (two-sided)
        CI     = b +/- t_{1 - alpha/2, df} * SE(b)                (Student t)
    Without `ar1_adjust`, n_eff = n. With it, n_eff = n (1 - r1) / (1 + r1) when the
    lag-1 autocorrelation r1 of the residuals is positive (n_eff = n otherwise),
    clipped to [3, n]. This widens SE and the CI for autocorrelated noise.

    Parameters
    ----------
    y : array-like, shape (..., n). One series per row along the last axis; NaN = missing.
    t : array-like, shape (n,). Time in decimal years, shared by all rows.
    alpha : float. The CI has confidence level 1 - alpha.
    ar1_adjust : bool. Apply the effective sample size correction above.

    Returns
    -------
    dict of arrays with shape y.shape[:-1] (NumPy scalars for 1-D input):
        slope, ci_low, ci_high, stderr (units of y per year), intercept, tstat,
        pvalue, n (valid points), n_eff, dof, resid_lag1_autocorr (r1, always computed).
    All float values are NaN when n < 3 or all valid times are equal.
    A constant series returns slope 0, stderr 0, p-value 1.

    Assumptions: the residuals are independent (or AR(1) with `ar1_adjust`),
    normally distributed with constant variance, and the trend is linear.
    r1 is computed from neighbours in the array, so gaps from NaN are skipped,
    not bridged.
    """
    y = np.asarray(y, dtype=float)
    t = np.asarray(t, dtype=float)
    if t.ndim != 1 or y.shape[-1] != t.size:
        raise ValueError(f"t must be 1-D with length y.shape[-1]; got t {t.shape}, y {y.shape}")

    valid = ~np.isnan(y)
    n = valid.sum(-1)
    const = np.where(valid, y, np.inf).min(-1) == np.where(valid, y, -np.inf).max(-1)
    with np.errstate(divide="ignore", invalid="ignore"):
        yw = np.where(valid, y, 0.0)
        tbar = np.where(valid, t, 0.0).sum(-1) / n
        ybar = yw.sum(-1) / n
        dt = np.where(valid, t - tbar[..., None], 0.0)
        sxx = (dt**2).sum(-1)
        # exact zero for constant series; floating sums would give noise / noise
        slope = np.where(const, 0.0, (dt * (yw - ybar[..., None])).sum(-1) / sxx)
        intercept = ybar - slope * tbar
        resid = np.where(valid, y - intercept[..., None] - slope[..., None] * t, 0.0)
        ssr = (resid**2).sum(-1)
        r1 = (resid[..., 1:] * resid[..., :-1]).sum(-1) / ssr  # invalid points have resid 0

        n_eff = n.astype(float)
        if ar1_adjust:
            n_eff = np.clip(np.where(r1 > 0, n * (1 - r1) / (1 + r1), n), 3, n)
        dof = n_eff - 2
        stderr = np.where(const, 0.0, np.sqrt(ssr / (dof * sxx)))
        tstat = np.where(const, 0.0, slope / stderr)
        pvalue = np.where(const, 1.0, 2 * stats.t.sf(np.abs(tstat), dof))
        half = np.where(const, 0.0, stats.t.ppf(1 - alpha / 2, dof) * stderr)

    out = dict(slope=slope, ci_low=slope - half, ci_high=slope + half, stderr=stderr,
               intercept=intercept, tstat=tstat, pvalue=pvalue, n_eff=n_eff, dof=dof,
               resid_lag1_autocorr=r1)
    bad = (n < 3) | ~(sxx > 0)
    out = {k: np.where(bad, np.nan, v)[()] for k, v in out.items()}
    out["n"] = n[()]
    return out
