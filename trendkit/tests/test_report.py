import json

import numpy as np
import pandas as pd
import pytest

from trendkit.report import trend_report

MONTHS = pd.date_range("2000-01-01", periods=300, freq="MS")
CYCLE = np.tile(8 * np.sin(2 * np.pi * np.arange(12) / 12), 25)


def _years(n):
    return np.arange(n) / 12


def _strict_json(r):
    return json.loads(json.dumps(r, allow_nan=False))  # fails on NaN or numpy types


def test_increasing_monthly_series():
    rng = np.random.default_rng(0)
    y = CYCLE + 0.05 * _years(300) + rng.normal(0, 0.5, 300)  # +0.5 per decade
    r = _strict_json(trend_report(y, MONTHS, units="K"))
    assert r["verdict"] == "increasing" and r["significant"] is True
    assert r["deseasonalized"] is True
    assert r["ci_low_per_decade"] < 0.5 < r["ci_high_per_decade"]
    assert r["slope_units"] == "K per decade"
    assert r["n_valid"] == r["n_total"] == 300
    assert r["period_start"] == "2000-01-01" and r["period_end"] == "2024-12-01"
    assert r["warnings"] == []


def test_decreasing_and_no_trend():
    rng = np.random.default_rng(1)
    noise = rng.normal(0, 0.5, 300)
    assert trend_report(CYCLE - 0.05 * _years(300) + noise, MONTHS)["verdict"] == "decreasing"
    r = trend_report(CYCLE + noise, MONTHS)
    assert r["verdict"] == "no significant trend" and r["significant"] is False


def test_annual_series_is_not_deseasonalized():
    years = pd.date_range("1990-01-01", periods=30, freq="YS")
    r = trend_report(np.arange(30.0), years)
    assert r["deseasonalized"] is False
    assert r["verdict"] == "increasing"
    assert r["slope_per_decade"] == pytest.approx(10.0, rel=1e-3)  # 1 per year, 365 vs 366-day years


def test_adjusted_pvalue_controls_significance():
    rng = np.random.default_rng(2)
    y = 0.02 * _years(300) + rng.normal(0, 0.5, 300)
    r = trend_report(y, MONTHS, deseasonalize=False)
    assert r["significant"]
    r = trend_report(y, MONTHS, deseasonalize=False, adjusted_pvalue=0.2)
    assert not r["significant"] and r["adjusted_pvalue"] == 0.2


def test_edge_cases_do_not_crash_and_stay_json():
    cases = {
        "all_nan": (np.full(300, np.nan), MONTHS),
        "constant": (np.full(300, 3.0), MONTHS),
        "one_point": ([1.0], MONTHS[:1]),
        "two_points": ([1.0, 2.0], MONTHS[:2]),
        "short": (np.arange(60.0), MONTHS[:60]),
        "ties": (np.round(np.random.default_rng(3).normal(size=300)), MONTHS),
        "monotonic": (np.arange(300.0), MONTHS),
    }
    out = {k: _strict_json(trend_report(y, d)) for k, (y, d) in cases.items()}
    assert out["all_nan"]["verdict"] == "insufficient data" and out["all_nan"]["slope_per_decade"] is None
    assert out["constant"]["verdict"] == "no significant trend"
    assert any("constant" in w for w in out["constant"]["warnings"])
    for k in ("one_point", "two_points", "short"):
        assert out[k]["verdict"] == "insufficient data"
        assert any("years of valid data" in w for w in out[k]["warnings"])
    assert not any("constant" in w for w in out["two_points"]["warnings"])
    short = trend_report(np.arange(60.0), MONTHS[:60], deseasonalize=False)
    assert short["slope_per_decade"] == pytest.approx(120.0, rel=1e-2)  # still reported
    assert out["monotonic"]["verdict"] == "increasing"
    raw = trend_report(np.arange(300.0), MONTHS, deseasonalize=False)  # deseasonalizing a ramp makes yearly steps (ties)
    assert raw["kendall_tau"] == 1


def test_missing_values():
    rng = np.random.default_rng(4)
    y = CYCLE + 0.05 * _years(300) + rng.normal(0, 0.5, 300)
    few = y.copy()
    few[[10, 11, 200]] = np.nan
    r = trend_report(few, MONTHS)
    assert r["n_valid"] == 297 and r["verdict"] == "increasing" and r["warnings"] == []
    many = y.copy()
    many[rng.uniform(size=300) < 0.4] = np.nan
    r = trend_report(many, MONTHS)
    assert r["verdict"] == "insufficient data"
    assert any("missing" in w for w in r["warnings"])


def test_unsorted_or_duplicate_dates_raise():
    with pytest.raises(ValueError, match="strictly increasing"):
        trend_report(np.arange(300.0), MONTHS[::-1])
    with pytest.raises(ValueError, match="one value per date"):
        trend_report(np.arange(10.0), MONTHS)


def test_autocorrelation_warnings():
    rng = np.random.default_rng(5)
    e = rng.normal(size=300)
    ar = np.zeros(300)
    for k in range(1, 300):
        ar[k] = 0.8 * ar[k - 1] + e[k]
    r = trend_report(ar, MONTHS, deseasonalize=False)
    assert any("Strong autocorrelation" in w for w in r["warnings"])
    r = trend_report(ar, MONTHS, method="original", deseasonalize=False)
    assert any("ignores autocorrelation" in w for w in r["warnings"])
    years = pd.date_range("1990-01-01", periods=25, freq="YS")
    r = trend_report(ar[:25], years)
    assert any("Short, autocorrelated" in w for w in r["warnings"])
