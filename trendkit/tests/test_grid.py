import numpy as np
import pandas as pd
import pytest
import xarray as xr

from trendkit.grid import area_weighted_mean, grid_trends
from trendkit.mannkendall import mann_kendall, sens_slope
from trendkit.seasonal import deseasonalize_monthly
from trendkit.timeutil import decimal_year

DATES = pd.date_range("2000-01-01", periods=300, freq="MS")
LAT = np.linspace(-47.5, 47.5, 20)
LON = np.linspace(-172, 176, 30)
PATCH = (slice(5, 10), slice(10, 16))  # 30 trending cells
LAND = (slice(15, 20), slice(0, 8))  # all-NaN block
TREND_PER_DECADE = 0.6  # 1.5 noise SD over 25 years


def _synthetic_grid(seed, phi=0.3):
    rng = np.random.default_rng(seed)
    nt, ny, nx = 300, LAT.size, LON.size
    e = rng.normal(size=(nt, ny, nx))
    noise = np.empty_like(e)
    noise[0] = e[0]
    for k in range(1, nt):
        noise[k] = phi * noise[k - 1] + np.sqrt(1 - phi**2) * e[k]
    cycle = 5 * np.sin(2 * np.pi * np.arange(nt) / 12)[:, None, None] * np.cos(np.deg2rad(LAT))[None, :, None]
    data = cycle + noise
    years = (decimal_year(DATES) - 2000)[:, None, None]
    data[:, PATCH[0], PATCH[1]] += TREND_PER_DECADE / 10 * years
    data[:, LAND[0], LAND[1]] = np.nan
    data[rng.uniform(size=data.shape) < 0.02] = np.nan  # scattered gaps
    data[:100, 0, 29] = np.nan  # one cell with 33% missing: fails the 80% rule
    return xr.DataArray(data, dims=("time", "lat", "lon"),
                        coords={"time": DATES, "lat": LAT, "lon": LON}, attrs={"units": "K"})


def test_patch_detected_and_fdr_controlled():
    in_patch = np.zeros((LAT.size, LON.size), bool)
    in_patch[PATCH] = True
    detection, fdp, raw_false = [], [], []
    for seed in range(10):
        ds = grid_trends(_synthetic_grid(seed))
        sig = ds["significant"].values
        detection.append(sig[in_patch].mean())
        fdp.append((sig & ~in_patch).sum() / max(sig.sum(), 1))
        raw_false.append(((ds["pvalue"].values < 0.05) & ~in_patch).sum())
    print(f"\nGrid 20x30, 10 seeds: patch detection {np.mean(detection):.3f}, "
          f"mean false discovery proportion {np.mean(fdp):.3f} (target q=0.05), "
          f"uncorrected p<0.05 false cells per map {np.mean(raw_false):.1f} of ~530 trend-free cells")
    assert np.mean(detection) >= 0.9
    assert np.mean(fdp) <= 0.08

    slope = ds["slope"].values[in_patch]
    assert np.nanmean(slope) == pytest.approx(TREND_PER_DECADE, abs=0.05)
    assert ds["slope"].attrs["units"] == "K per decade"


def test_nan_cells_and_minimum_data():
    ds = grid_trends(_synthetic_grid(0))
    land = ds.isel(lat=LAND[0], lon=LAND[1])
    assert np.isnan(land["pvalue"]).all() and (land["n_valid"] == 0).all() and not land["significant"].any()
    gappy = ds.isel(lat=0, lon=29)
    assert int(gappy["n_valid"]) < 0.8 * 300 and np.isnan(gappy["pvalue"]) and np.isnan(gappy["qvalue"])
    tested = np.isfinite(ds["pvalue"]).sum()
    assert tested == 20 * 30 - 5 * 8 - 1


def test_cell_matches_single_series_pipeline_and_dim_order():
    da = _synthetic_grid(1)
    ds = grid_trends(da.transpose("lat", "lon", "time"))
    assert ds["slope"].dims == ("lat", "lon")
    y = da.isel(lat=7, lon=12).values
    anom, _ = deseasonalize_monthly(y, DATES)
    mk = mann_kendall(anom)
    ss = sens_slope(anom, decimal_year(DATES), var_s=mk["var_s"])
    cell = ds.isel(lat=7, lon=12)
    assert float(cell["pvalue"]) == pytest.approx(mk["pvalue"], rel=1e-12)
    assert float(cell["slope"]) == pytest.approx(10 * ss["slope"], rel=1e-12)
    assert float(cell["ci_low"]) == pytest.approx(10 * ss["ci_low"], rel=1e-12)


def _lat_field():
    data = np.broadcast_to(LAT[None, :, None], (3, LAT.size, LON.size)).copy()
    return xr.DataArray(data, dims=("time", "lat", "lon"), coords={"time": DATES[:3], "lat": LAT, "lon": LON})


def test_area_weighted_mean():
    da = _lat_field()
    w = np.cos(np.deg2rad(LAT))
    assert np.allclose(area_weighted_mean(da), 0.0, atol=1e-12)  # symmetric latitudes

    north = LAT >= 10
    box = area_weighted_mean(da, (10, 90, -180, 180))
    assert np.allclose(box, (w[north] * LAT[north]).sum() / w[north].sum())

    mask = xr.DataArray(np.zeros((LAT.size, LON.size), bool), dims=("lat", "lon"), coords={"lat": LAT, "lon": LON})
    mask[north, :] = True
    xr.testing.assert_allclose(area_weighted_mean(da, mask), box)

    wrap = area_weighted_mean(da.assign_coords(lat=np.zeros(20)) + da["lon"], (-90, 90, 170, -170))
    assert np.allclose(wrap, np.mean(LON[(LON >= 170) | (LON <= -170)]))  # crosses the dateline

    gappy = da.copy()
    gappy[1, north, :] = np.nan
    gappy[2] = np.nan
    out = area_weighted_mean(gappy)
    south = ~north
    assert out[1] == pytest.approx((w[south] * LAT[south]).sum() / w[south].sum())
    assert np.isnan(out[2])

    with pytest.raises(ValueError, match="no grid cells"):
        area_weighted_mean(da, (60, 70, 0, 10))
