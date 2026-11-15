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
from ecodelta_engine.screen import (EVIDENCE_CLASSES, evidence, evidence_code, evidence_key, magnitude,
                                   magnitude_key, period_info, score, screen_region)

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


def test_score_tiers():
    rep = {"verdict": "increasing", "significant": True, "pvalue": 0.001}
    assert score({"report": None, "effect_size": None})["tier"] == 2
    assert score({"report": rep, "effect_size": -0.5}) == {"tier": 0, "significant": True, "pvalue": 0.001,
                                                          "effect_size": -0.5, "abs_effect_size": 0.5}


def test_evidence_code_thresholds():
    p = [0.005, 0.005, 0.03, 0.03, 0.07, 0.2, np.nan]
    lo = [0.1, -0.1, 0.1, -0.1, 0.1, -1, np.nan]
    hi = [0.3, 0.3, 0.3, 0.3, 0.3, 1, np.nan]
    assert [EVIDENCE_CLASSES[c] for c in evidence_code(p, lo, hi)] == \
        ["strong", "weak", "moderate", "weak", "weak", "none", "insufficient data"]
    assert int(evidence_code(0.001, -0.5, -0.2)) == 0  # a CI entirely below 0 also excludes 0


def rr(p, lo, hi, std, cov=1.0):
    rep = {"verdict": "increasing" if p < 0.05 else "no significant trend", "significant": p < 0.05, "pvalue": p,
           "slope_per_decade": (lo + hi) / 2, "ci_low_per_decade": lo, "ci_high_per_decade": hi}
    return {"report": rep, "effect_size": std, "fixed_mask": {"covered_fraction": cov}, "total_change": std,
            "residual_sd": 1.0, "standardized_change": std}


def test_evidence_coverage_cap_and_insufficient():
    assert evidence(rr(0.001, 0.1, 0.3, 1))["class"] == "strong"
    capped = evidence(rr(0.001, 0.1, 0.3, 1, cov=0.2))
    assert capped["class"] == "weak" and capped["capped_by_coverage"]
    assert evidence({"report": None})["class"] == "insufficient data"


def test_two_orderings_and_tie_breaks():
    """A small but certain trend leads by evidence; a large uncertain one leads by magnitude."""
    rrs = {"small_sure": rr(0.0001, 0.01, 0.02, 0.3), "big_unsure": rr(0.3, -1, 3, 2.5),
           "tie_a": rr(0.03, 0.1, 0.5, 1.0), "tie_b": rr(0.03, 0.1, 0.5, -1.0),
           "nodata": {"report": None, "effect_size": None, "fixed_mask": {"covered_fraction": 0.0},
                      "total_change": None, "residual_sd": None, "standardized_change": None}}
    entries = [{"variable": v, "score": score(r), "evidence": evidence(r), "magnitude": magnitude(r, "x")}
               for v, r in rrs.items()]
    assert [e["variable"] for e in sorted(entries, key=evidence_key)] == \
        ["small_sure", "tie_a", "tie_b", "big_unsure", "nodata"]
    assert [e["variable"] for e in sorted(entries, key=magnitude_key)] == \
        ["big_unsure", "tie_a", "tie_b", "small_sure", "nodata"]


def test_screen_region_exports_both_ranks(fixture_root):
    region = {r["id"]: r for r in load_regions()}["sahel"]
    ranked = screen_region(region, region_results(fixture_root, region), build_catalog(read_manifest(fixture_root), {}),
                           period_info(DATES))
    assert sorted(e["rank_by_magnitude"] for e in ranked) == [1, 2, 3, 4, 5]
    for e in ranked:
        m = e["magnitude"]
        if m["standardized_change"] is not None:
            assert m["standardized_change"] == pytest.approx(m["total_change"] / m["residual_sd"])
            assert m["total_change"] == pytest.approx(e["answers"]["how_much"]["total_change"])
