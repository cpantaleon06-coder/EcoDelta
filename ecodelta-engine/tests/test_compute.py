import numpy as np
import pandas as pd
import pytest
import xarray as xr
from trendkit import fixed_mask_mean, grid_trends, trend_report
from trendkit.grid import has_enough_data
from trendkit.timeutil import decimal_year

from ecodelta_engine.compute import compute_variable, region_result, regional_report, running_mean, sanity_checks
from ecodelta_engine.load import open_variable, read_manifest

DATES = pd.date_range("2001-01-01", periods=297, freq="MS").values


def test_regional_report_equals_plain_trend_report():
    rng = np.random.default_rng(1)
    y = 10 + 3 * np.sin(np.arange(297) * 2 * np.pi / 12) + 0.002 * np.arange(297) + rng.normal(0, 0.3, 297)
    anomalies, r = regional_report(y, DATES, "degC")
    direct = trend_report(y, DATES, units="degC")
    assert r == direct
    assert np.nanmean(anomalies) == pytest.approx(0, abs=1e-12)


def test_running_mean_is_trailing_and_needs_full_window():
    x = np.arange(24, dtype=float)
    rm = running_mean(x)
    assert np.isnan(rm[:11]).all() and rm[11] == pytest.approx(5.5) and rm[23] == pytest.approx(17.5)
    x[15] = np.nan
    assert np.isnan(running_mean(x)[15:27]).all()


@pytest.fixture(scope="module")
def arctic_patch(fixture_root):
    """Small t2m subset (12 x 30 cells) so grid_trends runs in about a second."""
    da = open_variable(fixture_root, read_manifest(fixture_root)["t2m"]).sel(lat=slice(67, 89), lon=slice(-179, -121))
    grid = grid_trends(da)
    valid = xr.DataArray(has_enough_data(grid.n_valid.values, decimal_year(da.time.values)),
                         dims=("lat", "lon"), coords={"lat": da.lat, "lon": da.lon})
    return da, grid, valid


def test_region_result_recovers_planted_trend(arctic_patch):
    da, grid, valid = arctic_patch
    r = region_result(da, valid, grid, {"id": "arctic", "box": [66.5, 90, -180, 180]})
    assert r["n_valid_cells"] == r["n_box_cells"] == 360 and r["covered_fraction"] == 1.0
    rep = r["report"]
    assert rep["verdict"] == "increasing" and rep["ci_low_per_decade"] < 0.85 < rep["ci_high_per_decade"]
    assert r["effect_size"] == pytest.approx(rep["slope_per_decade"] / np.nanstd(r["anomalies"], ddof=1))
    assert len(r["series"]) == len(r["anomalies"]) == len(r["running_mean"]) == 297
    m = r["map_cells"]
    assert m["n_tested"] == int(grid.pvalue.notnull().sum()) == 360
    assert m["n_significant"] == int(grid.significant.sum()) == m["n_significant_increasing"] + m["n_significant_decreasing"]
    assert r["cells_significant_fraction"] == m["share_significant"] == m["n_significant"] / 360


def test_region_mean_uses_fixed_mask(arctic_patch):
    """A cell missing its first 36 months (88% valid) passes the map's 80% rule but stays out of the
    regional mean, which uses the same cells every month (trendkit.fixed_mask_mean, 95% rule)."""
    da, grid, valid = arctic_patch
    gappy = da.copy()
    gappy[:36, 0, 0] = np.nan
    region = {"id": "arctic", "box": [66.5, 90, -180, 180]}
    r = region_result(gappy, valid, grid, region)
    fm = r["fixed_mask"]
    assert r["n_valid_cells"] == 360 and fm["n_cells"] == 359 and 0.99 < fm["covered_fraction"] < 1
    want, info = fixed_mask_mean(gappy, (66.5, 90, -180, 180))
    np.testing.assert_allclose(r["series"], want.values)
    assert fm["n_valid_months"] == info["n_valid"] == np.isfinite(r["series"]).sum()
    assert fm["n_months"] == 297 and 0.95 <= fm["weight_share_min"] <= fm["weight_share_max"] <= 1


def test_region_without_valid_cells_has_no_report(arctic_patch):
    da, grid, valid = arctic_patch
    r = region_result(da, valid, grid, {"id": "antarctica", "box": [-90, -60, -180, 180]})
    assert r["n_valid_cells"] == 0 and r["report"] is None and r["series"] is None
    assert r["fixed_mask"]["n_cells"] == 0 and r["fixed_mask"]["weight_share_min"] is None


def test_implausible_values_stop_the_run(fixture_root):
    with pytest.raises(ValueError, match="plausible range"):
        compute_variable(fixture_root, read_manifest(fixture_root)["t2m"], [], (0, 1))


def test_sanity_blocks_implausible_global_temperature_trend():
    def fake(slope, frac):
        rep = {"slope_per_decade": slope, "ci_low_per_decade": slope, "ci_high_per_decade": slope,
               "pvalue": 0.01, "verdict": "x"}
        return {"diagnostics": {"n_tested_cells": 10, "fraction_significant_fdr": frac},
                "regions": {"global": {"report": rep}}}
    report, blockers = sanity_checks({"t2m": fake(0.2, 0.6), "precip": fake(0.0, 0.0)})
    assert blockers == [] and "note" in report["t2m"] and "note" not in report["precip"]
    _, blockers = sanity_checks({"t2m": fake(-0.3, 0.1)})
    assert len(blockers) == 1 and "plausibility window" in blockers[0]
