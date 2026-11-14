import numpy as np
import pandas as pd

from trendkit.seasonal import deseasonalize_monthly

DATES = pd.date_range("2000-01-01", periods=120, freq="MS")
CYCLE = 10 * np.sin(2 * np.pi * np.arange(12) / 12)


def test_removes_fixed_cycle_exactly():
    y = np.tile(CYCLE, 10) + 3.0
    anom, clim = deseasonalize_monthly(y, DATES)
    np.testing.assert_allclose(clim, CYCLE + 3.0)
    np.testing.assert_allclose(anom, 0.0, atol=1e-12)


def test_nan_handling():
    rng = np.random.default_rng(0)
    y = np.tile(CYCLE, 10) + rng.normal(0, 0.1, 120)
    y[[5, 17, 50]] = np.nan
    y[np.arange(120) % 12 == 3] = np.nan  # every April missing
    anom, clim = deseasonalize_monthly(y, DATES)
    assert np.isnan(clim[3])
    assert np.isnan(anom[[3, 5, 17, 50]]).all()
    assert np.isfinite(anom).sum() == 120 - 10 - 3
    np.testing.assert_allclose(np.delete(clim, 3), np.delete(CYCLE, 3), atol=0.1)


def test_base_period():
    y = np.tile(CYCLE, 10) + np.repeat(np.arange(10.0), 12)  # step up by 1 each year
    _, clim = deseasonalize_monthly(y, DATES, base_period=("2000-01-01", "2001-12-31"))
    np.testing.assert_allclose(clim, CYCLE + 0.5)  # mean of years 0 and 1


def test_grid_input_matches_per_cell():
    rng = np.random.default_rng(1)
    g = rng.normal(size=(120, 3, 4)) + np.tile(CYCLE, 10)[:, None, None]
    g[:, 0, 0] = np.nan  # all-NaN cell must not crash
    anom, clim = deseasonalize_monthly(g, DATES)
    assert clim.shape == (12, 3, 4)
    a1, _ = deseasonalize_monthly(g[:, 2, 1], DATES)
    np.testing.assert_allclose(anom[:, 2, 1], a1)
    assert np.isnan(anom[:, 0, 0]).all()


def test_seasonal_cycle_hides_trend_until_removed():
    from trendkit.ols import ols_trend
    from trendkit.timeutil import decimal_year

    rng = np.random.default_rng(7)
    dates = pd.date_range("2000-01-01", periods=300, freq="MS")
    t = decimal_year(dates)
    true_slope = 0.02  # per year: 0.5 units over 25 years against a +/-10 seasonal cycle
    y = np.tile(CYCLE, 25) + true_slope * (t - t[0]) + rng.normal(0, 0.3, 300)
    raw = ols_trend(y, t)
    anom, _ = deseasonalize_monthly(y, dates)
    fixed = ols_trend(anom, t)
    print(f"\nraw:           slope {raw['slope']:+.4f}/yr, SE {raw['stderr']:.4f}, p {raw['pvalue']:.3f}"
          f"\ndeseasonalized: slope {fixed['slope']:+.4f}/yr, SE {fixed['stderr']:.4f}, p {fixed['pvalue']:.2e}")
    assert fixed["ci_low"] <= true_slope <= fixed["ci_high"]
    assert fixed["pvalue"] < 1e-6
    assert raw["pvalue"] > 0.05  # the cycle swamps the trend: not detected
    assert raw["stderr"] > 10 * fixed["stderr"]
