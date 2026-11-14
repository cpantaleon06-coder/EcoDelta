"""End-to-end demo on synthetic data: one series, then a grid, then a regional mean.

Run: python examples/demo_synthetic.py
"""

import json

import numpy as np
import pandas as pd
import xarray as xr

from trendkit import area_weighted_mean, grid_trends, trend_report

rng = np.random.default_rng(2026)
dates = pd.date_range("2000-01-01", periods=300, freq="MS")  # 25 years, monthly
years = np.arange(300) / 12


def ar1(shape, phi=0.4):
    e = rng.normal(size=shape)
    out = np.empty(shape)
    out[0] = e[0]
    for k in range(1, shape[0]):
        out[k] = phi * out[k - 1] + np.sqrt(1 - phi**2) * e[k]
    return out


# 1. One series: seasonal cycle + 0.3 K/decade warming + autocorrelated noise
series = 8 * np.sin(2 * np.pi * years) + 0.03 * years + 0.5 * ar1((300,))
print("1. One series, true trend +0.30 K per decade")
print(json.dumps(trend_report(series, dates, units="K"), indent=2))

# 2. A 30 x 60 grid: warming only in a tropical patch; the top rows have no data
lat = np.linspace(-88.5, 88.5, 30)
lon = np.linspace(-177, 177, 60)
cycle = 8 * np.sin(2 * np.pi * years)[:, None, None] * np.cos(np.deg2rad(lat))[None, :, None]
data = cycle + 0.5 * ar1((300, 30, 60))
patch = (slice(12, 18), slice(20, 35))
data[:, patch[0], patch[1]] += 0.03 * years[:, None, None]
data[:, 27:, :] = np.nan
da = xr.DataArray(data, dims=("time", "lat", "lon"),
                  coords={"time": dates, "lat": lat, "lon": lon}, attrs={"units": "K"})
ds = grid_trends(da)
truth = np.zeros((30, 60), bool)
truth[patch] = True
sig = ds["significant"].values
print("\n2. Grid 30 x 60, warming patch of", truth.sum(), "cells")
print(f"   tested cells: {int(np.isfinite(ds['pvalue']).sum())}, significant after FDR: {sig.sum()}")
print(f"   patch cells found: {(sig & truth).sum()}, false discoveries: {(sig & ~truth).sum()}")
print(f"   mean slope in patch: {float(ds['slope'].values[truth].mean()):.3f} {ds['slope'].attrs['units']}")

# 3. A user-drawn box over the patch, reduced to one series
box = (-20, 20, -60, 60)
regional = area_weighted_mean(da, box)
r = trend_report(regional.values, regional["time"].values, units="K")
print(f"\n3. Regional mean over lat {box[:2]}, lon {box[2:]}: "
      f"{r['slope_per_decade']:+.3f} K/decade "
      f"[{r['ci_low_per_decade']:+.3f}, {r['ci_high_per_decade']:+.3f}], p = {r['pvalue']:.2g}, "
      f"verdict: {r['verdict']}")
print("   (the box is wider than the patch: 15 of its 20 longitude columns warm, so expect 0.75 x 0.30 = 0.225)")
