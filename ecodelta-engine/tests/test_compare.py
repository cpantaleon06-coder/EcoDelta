"""Region comparison: trend test on D = A - B. Run with -s to print the measured Monte Carlo numbers.

Each synthetic region series = its own linear trend + a shared AR(1) signal (phi 0.4, SD 0.5) that both
regions see, as neighbouring regions do + an independent AR(1) (phi 0.4, SD 0.3) per region.
"""

import numpy as np
import pandas as pd
import pytest
import xarray as xr

from ecodelta_engine.compute import box_overlap, compare_pair, compare_regions
from ecodelta_engine.fixtures import ar1
from ecodelta_engine.load import LAT, LON
from ecodelta_engine.regions import load_regions

DATES = pd.date_range("2001-01-01", periods=297, freq="MS").values
YEARS = np.arange(297) / 12
SE5 = lambda n: np.sqrt(0.05 * 0.95 / n)  # binomial SE of a 5% rate


def pairs(seed, n, slope_a, slope_b):
    rng = np.random.default_rng(seed)
    shared = 0.5 * ar1(rng, (n,), 297, 0.4)
    a = slope_a / 10 * YEARS[:, None] + shared + 0.3 * ar1(rng, (n,), 297, 0.4)
    b = slope_b / 10 * YEARS[:, None] + shared + 0.3 * ar1(rng, (n,), 297, 0.4)
    return a, b


def test_different_slopes_are_detected():
    n = 200
    a, b = pairs(1, n, 0.6, 0.0)
    out = [compare_pair(a[:, i], b[:, i], DATES) for i in range(n)]
    power = np.mean([o["verdict"] == "trends differ" for o in out])
    slopes = np.array([o["difference_slope_per_decade"] for o in out])
    covered = np.mean([o["difference_ci_per_decade"][0] < 0.6 < o["difference_ci_per_decade"][1] for o in out])
    print(f"\nslopes 0.6 vs 0.0 per decade, {n} pairs: detected {power:.3f}, "
          f"mean difference slope {slopes.mean():.3f}, 95% CI covers 0.6 in {covered:.3f}")
    assert power >= 0.9 and slopes.mean() == pytest.approx(0.6, abs=0.03) and covered >= 0.9


def test_same_slope_false_positive_rate_near_5_percent():
    n = 1000
    a, b = pairs(2, n, 0.3, 0.3)
    out = [compare_pair(a[:, i], b[:, i], DATES) for i in range(n)]
    rate = np.mean([o["verdict"] == "trends differ" for o in out])
    print(f"\nsame slope 0.3 per decade, {n} pairs: false positive rate {rate:.3f} "
          f"(target 0.05, binomial SE {SE5(n):.4f})")
    assert rate <= 0.05 + 3 * SE5(n) and all(o["n_common_months"] == 297 for o in out)


def test_gaps_and_insufficient_data():
    a, b = pairs(3, 1, 0.5, 0.0)
    a, b = a[:, 0], b[:, 0]
    a[:10], b[-10:] = np.nan, np.nan
    assert compare_pair(a, b, DATES)["n_common_months"] == 277
    b[:200] = np.nan  # 77 common months: fails the 10-year rule
    o = compare_pair(a, b, DATES)
    assert o["verdict"] == "insufficient data" and o["pvalue"] is None and o["difference_ci_per_decade"] is None


def test_box_overlap():
    r = {x["id"]: x["box"] for x in load_regions()}
    assert box_overlap(r["global"], r["sahel"], LAT, LON) == 1.0
    assert box_overlap(r["sahel"], r["australia"], LAT, LON) == 0.0
    assert 0 < box_overlap(r["western_europe"], r["mediterranean"], LAT, LON) < 1


def test_compare_regions_pairs_q_and_missing_region():
    a, b = pairs(4, 3, 0.8, 0.0)
    rep = {"verdict": "increasing", "slope_per_decade": 0.8, "ci_low_per_decade": 0.5,
           "ci_high_per_decade": 1.1, "pvalue": 0.001}
    rr = lambda x: {"anomalies": x, "report": rep, "fixed_mask": {"covered_fraction": 1.0}}
    regions = [{"id": "r1", "box": [0, 10, 0, 10]}, {"id": "r2", "box": [4, 20, 4, 20]},
               {"id": "r3", "box": [-20, -10, 0, 10]}, {"id": "r4", "box": [30, 40, 0, 10]}]
    grid = xr.Dataset(coords={"lat": LAT, "lon": LON})
    res = {"dates": DATES, "grid": grid, "regions": {"r1": rr(a[:, 0]), "r2": rr(b[:, 0]), "r3": rr(b[:, 1]),
                                                       "r4": {"anomalies": None, "report": None,
                                                              "fixed_mask": {"covered_fraction": 0.0}}}}
    out = compare_regions(res, regions)
    assert [(p["region_a"], p["region_b"]) for p in out] == \
        [("r1", "r2"), ("r1", "r3"), ("r1", "r4"), ("r2", "r3"), ("r2", "r4"), ("r3", "r4")]
    by = {(p["region_a"], p["region_b"]): p for p in out}
    assert by[("r1", "r2")]["verdict"] == "trends differ" and not by[("r1", "r2")]["independent"]
    assert by[("r1", "r3")]["independent"] and by[("r1", "r3")]["overlap_fraction"] == 0
    assert by[("r1", "r4")]["verdict"] == "insufficient data" and by[("r1", "r4")]["q_across_pairs"] is None
    assert by[("r1", "r4")]["trend_b"]["evidence_class"] == "insufficient data"
    tested = [p for p in out if p["pvalue"] is not None]
    assert len(tested) == 3 and all(p["q_across_pairs"] >= p["pvalue"] * (1 - 1e-12) for p in tested)  # largest p: q = 3p/3
