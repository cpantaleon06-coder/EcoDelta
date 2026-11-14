import numpy as np
import pandas as pd
import pytest
import xarray as xr
from trendkit import grid_trends
from trendkit.grid import has_enough_data
from trendkit.timeutil import decimal_year

from ecodelta_engine.catalog import build_catalog
from ecodelta_engine.compute import region_result, regional_report
from ecodelta_engine.fixtures import ar1
from ecodelta_engine.load import open_variable, read_manifest
from ecodelta_engine.regions import load_regions
from ecodelta_engine.screen import period_info, score, screen_region

DATES = pd.date_range("2001-01-01", periods=297, freq="MS").values


def region_results(root, region, pad=2):
    """compute.region_result for every variable on a padded subset around the box (fast)."""
    la0, la1, lo0, lo1 = region["box"]
    out = {}
    for v, e in read_manifest(root).items():
        da = open_variable(root, e).sel(lat=slice(la0 - pad, la1 + pad), lon=slice(lo0 - pad, lo1 + pad))
        g = grid_trends(da)
        valid = xr.DataArray(has_enough_data(g.n_valid.values, decimal_year(da.time.values)),
                             dims=("lat", "lon"), coords={"lat": da.lat, "lon": da.lon})
        out[v] = region_result(da, valid, g, region)
    return out


@pytest.mark.parametrize("rid,first", [("sahel", "precip"), ("mediterranean", "soil_moisture_0_10cm")])
def test_planted_trend_ranks_first(fixture_root, rid, first):
    region = {r["id"]: r for r in load_regions()}[rid]
    ranked = screen_region(region, region_results(fixture_root, region), build_catalog(read_manifest(fixture_root), {}),
                           period_info(DATES))
    assert ranked[0]["variable"] == first and ranked[0]["score"]["significant"]
    assert [e["rank"] for e in ranked] == [1, 2, 3, 4, 5]
    assert ranked[-1]["variable"] != first


def test_pure_noise_is_rarely_significant():
    """400 trend-free regional series (seasonal cycle + AR(1) noise): the share called significant must
    stay within the 5% false-positive rate plus 3 binomial standard errors."""
    n = 400
    rng = np.random.default_rng(7)
    noise = ar1(rng, (n,), 297, 0.4)
    season = 5 * np.cos(2 * np.pi * np.arange(297) / 12)
    hits = 0
    for i in range(n):
        _, rep = regional_report(10 + season + noise[:, i], DATES, "x")
        hits += score({"report": rep, "effect_size": 0.0})["significant"]
    assert hits / n <= 0.05 + 3 * np.sqrt(0.05 * 0.95 / n)


def test_score_tiers_and_order():
    rep = lambda p, sig: {"verdict": "increasing" if sig else "no significant trend", "significant": sig, "pvalue": p}
    rrs = {"a": {"report": rep(0.2, False), "effect_size": 2.0},
           "b": {"report": rep(0.01, True), "effect_size": 0.1},
           "c": {"report": None, "effect_size": None},
           "d": {"report": rep(0.001, True), "effect_size": -0.5}}
    from ecodelta_engine.screen import _key
    order = sorted(rrs, key=lambda k: _key(score(rrs[k])))
    assert order == ["d", "b", "a", "c"]
    assert score(rrs["c"])["tier"] == 2 and score(rrs["d"])["abs_effect_size"] == 0.5
