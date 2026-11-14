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


def _acf(x):
    """Biased sample autocorrelation rho_k = sum(d_i d_{i+k}) / sum(d_i^2), d = x - mean,
    for lags 0..n-1 along the last axis. NaN are gaps: pairs that touch a gap are skipped,
    and lags count array positions (time steps), not valid points."""
    valid = ~np.isnan(x)
    with np.errstate(divide="ignore", invalid="ignore"):
        d = np.where(valid, x - np.nansum(x, -1, keepdims=True) / valid.sum(-1, keepdims=True), 0.0)
        nfft = 1 << (2 * x.shape[-1] - 1).bit_length()
        f = np.fft.rfft(d, nfft)
        acov = np.fft.irfft(f.real**2 + f.imag**2, nfft)[..., : x.shape[-1]]
        return acov / acov[..., :1]


METHODS = ("original", "hamed_rao", "yue_wang", "tfpw")
DEFAULT_METHOD = "yue_wang"  # chosen from the Monte Carlo in tests/test_autocorr_montecarlo.py


def mann_kendall(y, method=DEFAULT_METHOD):
    """Mann-Kendall test for a monotonic trend (Mann 1945, Kendall 1975), with optional
    corrections for autocorrelated data.

    Formulas (original test):
        S      = sum over i < j of sign(y_j - y_i)
        Var(S) = [n(n-1)(2n+5) - sum over tie groups of t(t-1)(2t+5)] / 18
        Z      = (S - 1)/sqrt(Var(S)) if S > 0;  0 if S = 0;  (S + 1)/sqrt(Var(S)) if S < 0
        p      = 2 * (1 - Phi(|Z|))           (two-sided, normal approximation)
        tau    = S / (n(n-1)/2)               (Kendall tau-a)
    The +/-1 is the continuity correction.

    Autocorrelation methods. Each first removes the trend with Sen's slope per time step,
    x_i = y_i - b * i, so that the trend itself is not mistaken for autocorrelation:
      "hamed_rao" (Hamed and Rao 1998): Var(S) *= n/n*, with
          n/n* = 1 + 2 / (n(n-1)(n-2)) * sum_k (n-k)(n-k-1)(n-k-2) rho_k,
          where rho_k is the autocorrelation of the ranks of x, and only lags with
          |rho_k| > 1.96 / sqrt(n) (significant at 5%) are included.
      "yue_wang" (Yue and Wang 2004 effective sample size):
          Var(S) *= 1 + 2 sum_{k=1}^{n-1} (1 - k/n) rho_k,
          with rho_k taken as r1^k (AR(1) model), r1 = lag-1 autocorrelation of x,
          and the factor floored at 1 (only positive autocorrelation is corrected).
          Both the AR(1) form and the floor are our choices: summing raw sample
          autocorrelations over all lags is unstable, and the floor halved false
          alarms for short white-noise series in our Monte Carlo (docs/METHODS.md).
          This is the default: it was the only variant that held the false-alarm
          rate near 5% for n=300 at phi = 0, 0.3 and 0.6.
      "tfpw" (trend-free pre-whitening, Yue et al. 2002): run the original test on
          w_i = x_i - r1 x_{i-1} + b * i, which has one point fewer.

    Parameters
    ----------
    y : array-like, shape (..., n), in time order along the last axis, equally spaced
        in time (the corrections count lags in array positions); NaN = missing.
    method : one of "original", "hamed_rao", "yue_wang", "tfpw".

    Returns
    -------
    dict with shape y.shape[:-1] (NumPy scalars for 1-D input):
        s, var_s (corrected), var_factor (correction applied to Var(S), 1 for
        "original" and "tfpw"), z, pvalue, tau (dimensionless), n (valid points in y).
    Float values are NaN when n < 3. A constant series gives z 0, p-value 1.

    Assumptions: "original" assumes independent observations; the corrections assume
    the dependence is short-range and well estimated from the series itself, which
    is hard for short series. All use the normal approximation (roughly n >= 10).
    The test is non-parametric: it needs no normality and is robust to outliers, but
    it detects monotonic change, not its size (use `sens_slope` for that).
    """
    if method not in METHODS:
        raise ValueError(f"method must be one of {METHODS}, got {method!r}")
    y = np.asarray(y, dtype=float)
    x = y
    if method != "original":
        step = np.arange(y.shape[-1], dtype=float)
        b = np.asarray(sens_slope(y, step)["slope"])[..., None]
        detrended = y - b * step
    if method == "tfpw":
        r1 = np.nan_to_num(_acf(detrended)[..., 1:2])  # constant series: 0/0, no autocorrelation
        x = detrended[..., 1:] - r1 * detrended[..., :-1] + b * step[1:]
    s, var, n = _s_and_var(x)

    factor = np.ones_like(var)
    with np.errstate(divide="ignore", invalid="ignore"):
        if method in ("hamed_rao", "yue_wang"):
            nn = n[..., None]
            k = np.arange(1, y.shape[-1])
        if method == "hamed_rao":
            rho = _acf(stats.rankdata(detrended, axis=-1, nan_policy="omit"))[..., 1:]
            keep = np.abs(rho) > stats.norm.ppf(0.975) / np.sqrt(nn)
            w = np.clip((nn - k) * (nn - k - 1) * (nn - k - 2), 0, None)
            factor = 1 + 2 / (n * (n - 1) * (n - 2)) * np.where(keep, w * rho, 0).sum(-1)
        elif method == "yue_wang":
            r1 = _acf(detrended)[..., 1:2]
            factor = np.maximum(1 + 2 * (np.clip(1 - k / nn, 0, None) * r1**k).sum(-1), 1.0)
        factor = np.where(np.isfinite(factor), factor, 1.0)  # constant series: no autocorrelation defined
        var = var * factor
        z = np.where(s > 0, (s - 1) / np.sqrt(var), np.where(s < 0, (s + 1) / np.sqrt(var), 0.0))
        tau = s / (n * (n - 1) / 2)  # n counts the series actually tested (n - 1 for "tfpw")
    out = dict(s=s, var_s=var, var_factor=factor, z=z, pvalue=2 * stats.norm.sf(np.abs(z)), tau=tau)
    out = {k: np.where(n < 3, np.nan, v)[()] for k, v in out.items()}
    out["n"] = (~np.isnan(y)).sum(-1)[()]
    return out


def sens_slope(y, t, alpha=0.05, var_s=None):
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
    var_s : array-like with shape y.shape[:-1], optional. Var(S) to build the CI from,
        typically the autocorrelation-corrected `mann_kendall(y, method)["var_s"]`, so
        the CI is consistent with that test. Default: the uncorrected Var(S).

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
        k = np.clip(np.nan_to_num(k), 0, np.maximum(m - 1, 0)).astype(int)  # NaN var_s: masked below
        return np.take_along_axis(slopes, k[..., None], axis=-1)[..., 0]

    n = (~np.isnan(y)).sum(-1)
    if var_s is None:
        _, var_s, _ = _s_and_var(y)
    c = stats.norm.ppf(1 - alpha / 2) * np.sqrt(var_s)
    out = dict(slope=0.5 * (rank((m - 1) // 2) + rank(m // 2)),
               ci_low=rank(np.round((m - c) / 2) - 1),
               ci_high=rank(np.round((m + c) / 2)))
    out = {k: np.where(n < 3, np.nan, v)[()] for k, v in out.items()}
    out["n"] = n.astype(int)[()]
    return out
