import numpy as np
import pymannkendall as pmk
import pytest
from scipy import stats

from trendkit.mannkendall import mann_kendall, sens_slope

T = 2000 + np.arange(300) / 12


def _check_against_pymannkendall(y):
    ours = mann_kendall(y, "original")
    ref = pmk.original_test(y)
    assert ours["s"] == ref.s
    assert ours["var_s"] == pytest.approx(ref.var_s, rel=1e-12)
    assert ours["z"] == pytest.approx(ref.z, rel=1e-12)
    assert ours["pvalue"] == pytest.approx(ref.p, rel=1e-9, abs=1e-15)
    assert ours["tau"] == pytest.approx(ref.Tau, rel=1e-12)


@pytest.mark.parametrize("seed", range(5))
def test_mann_kendall_matches_pymannkendall_tie_free(seed):
    rng = np.random.default_rng(seed)
    _check_against_pymannkendall(0.01 * seed * T + rng.normal(size=T.size))


def test_mann_kendall_matches_pymannkendall_with_ties_and_nan():
    rng = np.random.default_rng(10)
    y = np.round(0.05 * (T - T[0]) + rng.normal(size=T.size))  # integers: many ties
    y[[4, 90, 91]] = np.nan
    _check_against_pymannkendall(y)


@pytest.mark.parametrize("seed", range(5))
def test_sens_slope_matches_scipy_theilslopes(seed):
    rng = np.random.default_rng(100 + seed)
    y = 0.02 * T + rng.standard_t(3, T.size)  # heavy-tailed noise
    ours = sens_slope(y, T)
    ref = stats.theilslopes(y, T, alpha=0.95)
    assert ours["slope"] == pytest.approx(ref.slope, rel=1e-12)
    assert (ours["ci_low"], ours["ci_high"]) == pytest.approx((ref.low_slope, ref.high_slope), rel=1e-12)


def test_sens_slope_ignores_nan_and_matches_scipy_on_the_rest():
    rng = np.random.default_rng(11)
    y = 0.02 * T + rng.normal(size=T.size)
    y[[0, 50, 51, 299]] = np.nan
    keep = ~np.isnan(y)
    ours, ref = sens_slope(y, T), stats.theilslopes(y[keep], T[keep])
    assert ours["n"] == 296
    assert ours["slope"] == pytest.approx(ref.slope, rel=1e-12)
    assert (ours["ci_low"], ours["ci_high"]) == pytest.approx((ref.low_slope, ref.high_slope), rel=1e-12)


def test_rows_match_one_series_at_a_time():
    rng = np.random.default_rng(12)
    Y = rng.normal(size=(4, 60)) + 0.1 * np.arange(60)
    Y[1, ::5] = np.nan
    Y[2] = np.nan
    t = np.arange(60.0)
    mk, ss = mann_kendall(Y, "original"), sens_slope(Y, t)
    for k in range(4):
        one_mk, one_ss = mann_kendall(Y[k], "original"), sens_slope(Y[k], t)
        for key in ("s", "pvalue", "tau"):
            np.testing.assert_allclose(mk[key][k], one_mk[key])
        for key in ("slope", "ci_low", "ci_high"):
            np.testing.assert_allclose(ss[key][k], one_ss[key])


def test_edge_cases():
    t = np.arange(30.0)
    nan = np.full(30, np.nan)
    assert np.isnan(mann_kendall(nan, "original")["pvalue"]) and np.isnan(sens_slope(nan, t)["slope"])
    assert np.isnan(mann_kendall([1.0, 2.0], "original")["pvalue"])
    assert np.isnan(sens_slope([1.0, 2.0], [0.0, 1.0])["slope"])
    assert np.isnan(sens_slope([1.0], [0.0])["slope"])

    const = np.full(30, 4.2)
    mk = mann_kendall(const, "original")
    assert (mk["s"], mk["z"], mk["pvalue"]) == (0, 0, 1)
    ss = sens_slope(const, t)
    assert (ss["slope"], ss["ci_low"], ss["ci_high"]) == (0, 0, 0)

    up = mann_kendall(t, "original")  # perfectly monotonic
    assert up["tau"] == 1 and up["pvalue"] < 1e-9
    assert sens_slope(3 * t, t)["slope"] == pytest.approx(3)

    with pytest.raises(ValueError, match="strictly increasing"):
        sens_slope(t, t[::-1])


def test_robust_to_outliers():
    rng = np.random.default_rng(13)
    t = np.arange(100.0)
    y = 0.5 * t + rng.normal(size=100)
    y[::10] += 500  # 10% wild outliers
    assert sens_slope(y, t)["slope"] == pytest.approx(0.5, abs=0.05)


def _ar1(rng, phi, shape):
    """AR(1) noise with unit marginal variance, started from its stationary distribution."""
    shape = np.atleast_1d(shape)
    e = rng.normal(size=shape)
    out = np.empty(shape)
    out[..., 0] = e[..., 0]
    for k in range(1, shape[-1]):
        out[..., k] = phi * out[..., k - 1] + np.sqrt(1 - phi**2) * e[..., k]
    return out


@pytest.mark.parametrize("seed", range(4))
def test_hamed_rao_and_tfpw_match_pymannkendall(seed):
    rng = np.random.default_rng(200 + seed)
    y = 0.003 * seed * np.arange(300) + _ar1(rng, 0.5, 300)
    for ours, ref in ((mann_kendall(y, "hamed_rao"), pmk.hamed_rao_modification_test(y)),
                      (mann_kendall(y, "tfpw"), pmk.trend_free_pre_whitening_modification_test(y))):
        assert ours["s"] == ref.s
        assert ours["var_s"] == pytest.approx(ref.var_s, rel=1e-9)
        assert ours["pvalue"] == pytest.approx(ref.p, rel=1e-7, abs=1e-15)


def test_yue_wang_ar1_factor_approaches_theory():
    rng = np.random.default_rng(300)
    y = _ar1(rng, 0.6, 5000)
    factor = mann_kendall(y, "yue_wang")["var_factor"]
    assert factor == pytest.approx((1 + 0.6) / (1 - 0.6), rel=0.1)  # large-n limit for AR(1)


@pytest.mark.parametrize("method", ["hamed_rao", "yue_wang", "tfpw"])
def test_corrected_methods_edge_cases_and_rows(method):
    t = np.arange(40.0)
    assert np.isnan(mann_kendall(np.full(40, np.nan), method)["pvalue"])
    assert mann_kendall(np.full(40, 2.0), method)["pvalue"] == 1
    assert mann_kendall(t, method)["pvalue"] < 1e-3
    assert np.isnan(mann_kendall([1.0, 2.0], method)["pvalue"])
    rng = np.random.default_rng(301)
    Y = rng.normal(size=(3, 40)) + 0.05 * t
    Y[1, [3, 4, 20]] = np.nan
    batch = mann_kendall(Y, method)
    for k in range(3):
        np.testing.assert_allclose(batch["pvalue"][k], mann_kendall(Y[k], method)["pvalue"])
