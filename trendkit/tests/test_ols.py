import numpy as np
import pytest
import statsmodels.api as sm
from scipy import stats

from trendkit.ols import ols_trend

T = 2000 + np.arange(300) / 12  # 25 years of monthly time steps, in years


def test_matches_scipy_linregress_and_statsmodels():
    rng = np.random.default_rng(0)
    y = 0.03 * T + rng.normal(0, 1, T.size)
    r = ols_trend(y, T)
    ref = stats.linregress(T, y)
    assert r["slope"] == pytest.approx(ref.slope, rel=1e-10)
    assert r["intercept"] == pytest.approx(ref.intercept, rel=1e-8)
    assert r["stderr"] == pytest.approx(ref.stderr, rel=1e-10)
    assert r["pvalue"] == pytest.approx(ref.pvalue, rel=1e-8)
    ci = sm.OLS(y, sm.add_constant(T)).fit().conf_int(alpha=0.05)[1]
    assert (r["ci_low"], r["ci_high"]) == pytest.approx(tuple(ci), rel=1e-8)


def test_nan_points_are_dropped():
    rng = np.random.default_rng(1)
    y = 0.03 * T + rng.normal(0, 1, T.size)
    y[[3, 40, 41, 200]] = np.nan
    keep = ~np.isnan(y)
    r = ols_trend(y, T)
    ref = stats.linregress(T[keep], y[keep])
    assert r["n"] == 296
    assert r["slope"] == pytest.approx(ref.slope, rel=1e-10)
    assert r["pvalue"] == pytest.approx(ref.pvalue, rel=1e-8)


def test_rows_match_one_series_at_a_time():
    rng = np.random.default_rng(2)
    Y = rng.normal(size=(5, T.size)) + 0.02 * T
    Y[1, ::7] = np.nan
    Y[3] = np.nan
    batch = ols_trend(Y, T)
    for k in range(5):
        one = ols_trend(Y[k], T)
        for key in ("slope", "pvalue", "ci_low", "ci_high", "n"):
            np.testing.assert_allclose(batch[key][k], one[key], rtol=1e-12)


def test_edge_cases():
    assert np.isnan(ols_trend(np.full(T.size, np.nan), T)["slope"])  # all NaN
    assert np.isnan(ols_trend([1.0, 2.0], [0.0, 1.0])["pvalue"])  # too short
    c = ols_trend(np.full(T.size, 0.1), T)  # constant
    assert (c["slope"], c["stderr"], c["pvalue"]) == (0.0, 0.0, 1.0)
    line = ols_trend(2.0 * T + 1, T)  # perfect line
    assert line["slope"] == pytest.approx(2.0)
    assert line["pvalue"] < 1e-12
    assert np.isnan(ols_trend([1.0, 2.0, 3.0], [5.0, 5.0, 5.0])["slope"])  # no time spread


def test_ar1_adjust_widens_ci_only_when_residuals_are_autocorrelated():
    rng = np.random.default_rng(3)
    white = rng.normal(size=T.size)
    ar = np.zeros(T.size)
    for k in range(1, T.size):
        ar[k] = 0.6 * ar[k - 1] + white[k]
    plain, adj = ols_trend(ar, T), ols_trend(ar, T, ar1_adjust=True)
    assert adj["n_eff"] < 0.5 * plain["n_eff"]
    assert adj["stderr"] > 1.5 * plain["stderr"]
    assert adj["slope"] == plain["slope"]
    w_plain, w_adj = ols_trend(white, T), ols_trend(white, T, ar1_adjust=True)
    assert w_adj["stderr"] == pytest.approx(w_plain["stderr"], rel=0.15)


def test_ci_coverage_and_false_positive_rate_monte_carlo():
    rng = np.random.default_rng(42)
    true_slope = 0.02  # units per year
    sims = 1000
    y = true_slope * (T - T[0]) + rng.normal(0, 0.5, (sims, T.size))
    r = ols_trend(y, T)
    coverage = np.mean((r["ci_low"] <= true_slope) & (true_slope <= r["ci_high"]))
    bias = np.mean(r["slope"]) - true_slope
    print(f"\nOLS 95% CI coverage over {sims} sims: {coverage:.3f}; mean slope bias {bias:+.2e}/yr")
    assert abs(bias) < 1e-3
    assert 0.93 <= coverage <= 0.97  # binomial SE at n=1000 is about 0.007

    sims = 5000
    noise = rng.normal(0, 1, (sims, T.size))
    fpr = np.mean(ols_trend(noise, T)["pvalue"] < 0.05)
    print(f"OLS false-positive rate, white noise, {sims} sims, alpha 0.05: {fpr:.4f}")
    assert 0.04 <= fpr <= 0.06  # binomial SE at n=5000 is about 0.003
