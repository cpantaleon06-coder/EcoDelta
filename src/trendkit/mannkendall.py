"""Mann-Kendall trend test, Sen's slope, and autocorrelation handling."""

import numpy as np
from scipy import stats

from .timeutil import require_increasing


def _s_and_var(y):
    """Mann-Kendall S and its variance with tie correction, along the last axis.

    S = sum over pairs i < j of sign(y_j - y_i), using only pairs where both are valid.
    Var(S) = [n(n-1)(2n+5) - sum_g t_g(t_g-1)(2t_g+5)] / 18, t_g = size of tie group g.
    The tie sum is computed per value: each value in a group of size c adds (c-1)(2c+5).
    """
    valid = ~np.isnan(y)
    n = valid.sum(-1).astype(float)
    i, j = np.triu_indices(y.shape[-1], k=1)
    s = np.nansum(np.sign(y[..., j] - y[..., i]), axis=-1)
    group = (y[..., :, None] == y[..., None, :]).sum(-1)  # 0 for NaN
    ties = np.where(valid, (group - 1) * (2 * group + 5), 0).sum(-1)
    var = (n * (n - 1) * (2 * n + 5) - ties) / 18
    return s, var, n


def mann_kendall(y):
    """Mann-Kendall test for a monotonic trend (Mann 1945, Kendall 1975).

    Formulas:
        S      = sum over i < j of sign(y_j - y_i)
        Var(S) = [n(n-1)(2n+5) - sum over tie groups of t(t-1)(2t+5)] / 18
        Z      = (S - 1)/sqrt(Var(S)) if S > 0;  0 if S = 0;  (S + 1)/sqrt(Var(S)) if S < 0
        p      = 2 * (1 - Phi(|Z|))           (two-sided, normal approximation)
        tau    = S / (n(n-1)/2)               (Kendall tau-a)
    The +/-1 is the continuity correction.

    Parameters
    ----------
    y : array-like, shape (..., n), in time order along the last axis; NaN = missing.

    Returns
    -------
    dict with shape y.shape[:-1] (NumPy scalars for 1-D input):
        s, var_s, z, pvalue, tau (dimensionless), n (valid points).
    Float values are NaN when n < 3. A constant series gives z 0, p-value 1.

    Assumptions: observations are independent (no autocorrelation) and n is
    large enough for the normal approximation (roughly n >= 10). The test is
    non-parametric: it needs no normality and is robust to outliers, but it
    detects monotonic change, not its size (use `sens_slope` for that).
    """
    y = np.asarray(y, dtype=float)
    s, var, n = _s_and_var(y)
    with np.errstate(divide="ignore", invalid="ignore"):
        z = np.where(s > 0, (s - 1) / np.sqrt(var), np.where(s < 0, (s + 1) / np.sqrt(var), 0.0))
        tau = s / (n * (n - 1) / 2)
    out = dict(s=s, var_s=var, z=z, pvalue=2 * stats.norm.sf(np.abs(z)), tau=tau)
    out = {k: np.where(n < 3, np.nan, v)[()] for k, v in out.items()}
    out["n"] = n.astype(int)[()]
    return out


def sens_slope(y, t, alpha=0.05):
    """Theil-Sen slope with its non-parametric confidence interval (Sen 1968, Gilbert 1987).

    Formulas:
        slope = median over i < j of (y_j - y_i) / (t_j - t_i)       (N = n(n-1)/2 pairwise slopes)
        C     = z_{1 - alpha/2} * sqrt(Var(S))                        (Var(S) as in `mann_kendall`)
        M1    = (N - C)/2,  M2 = (N + C)/2
        CI    = [M1-th, (M2 + 1)-th] of the pairwise slopes sorted ascending (1-based ranks,
                rounded to the nearest integer and clipped to [1, N])
    The rank rounding follows the same convention as scipy.stats.theilslopes.

    Parameters
    ----------
    y : array-like, shape (..., n). NaN = missing.
    t : array-like, shape (n,). Time in decimal years, strictly increasing.
    alpha : float. The CI has confidence level 1 - alpha.

    Returns
    -------
    dict with shape y.shape[:-1] (NumPy scalars for 1-D input):
        slope, ci_low, ci_high (units of y per year), n (valid points).
    Float values are NaN when n < 3.

    Assumptions: a linear (or at least monotonic) trend; the CI assumes
    independent observations, like the Mann-Kendall variance it is built on.
    Robust to outliers: up to about 29% of points can be corrupted without
    breaking the estimate.
    """
    y = np.asarray(y, dtype=float)
    t = require_increasing(t)
    if y.shape[-1] != t.size:
        raise ValueError(f"t has {t.size} points, y has {y.shape[-1]}")
    i, j = np.triu_indices(t.size, k=1)
    slopes = np.sort((y[..., j] - y[..., i]) / (t[j] - t[i]), axis=-1)  # NaN pairs sort last
    if slopes.shape[-1] == 0:
        slopes = np.full(y.shape[:-1] + (1,), np.nan)
    m = (~np.isnan(slopes)).sum(-1)  # valid pairs

    def rank(k):  # 0-based index into the sorted valid slopes, clipped to range
        k = np.clip(k, 0, np.maximum(m - 1, 0)).astype(int)
        return np.take_along_axis(slopes, k[..., None], axis=-1)[..., 0]

    _, var, n = _s_and_var(y)
    c = stats.norm.ppf(1 - alpha / 2) * np.sqrt(var)
    out = dict(slope=0.5 * (rank((m - 1) // 2) + rank(m // 2)),
               ci_low=rank(np.round((m - c) / 2) - 1),
               ci_high=rank(np.round((m + c) / 2)))
    out = {k: np.where(n < 3, np.nan, v)[()] for k, v in out.items()}
    out["n"] = n.astype(int)[()]
    return out
