"""Synthetic proof: a changing set of cells creates a trend that the fixed mask removes.

Every cell has NO trend. Half of the cells are warm (mean 20), half are cold (mean 0). Each cold
cell is missing in a month with probability 15% at the start, falling linearly to 0% at the end
(like cloud or sea-ice gaps that become rarer), so it is valid in about 92.5% of months: it passes
the 80% data rule, so the old regional mean (area_weighted_mean over cells that pass has_enough_data)
uses it, and fails the 95% fixed-mask rule. Early months average fewer cold cells, so the old mean
falls over time. Noise: a regional AR(1) component (phi 0.5, SD 0.3) shared by all cells plus an
independent AR(1) per cell (phi 0.3, SD 1); 1% scattered gaps everywhere.
Run with -s to print the measured numbers (they are quoted in docs/METHODS.md, section 7).
"""

import numpy as np
import pandas as pd
import xarray as xr

from trendkit import trend_report
from trendkit.grid import area_weighted_mean, fixed_mask_mean, has_enough_data
from trendkit.timeutil import decimal_year

SIMS = 200
DATES = pd.date_range("2001-01-01", periods=297, freq="MS")
LAT = np.arange(31.0, 52.0, 4.0)  # 6 rows
LON = np.arange(1.0, 40.0, 4.0)  # 10 columns
COLD = LAT >= 43  # upper 3 rows


def _ar1(rng, phi, shape):
    e = rng.normal(size=shape)
    out = np.empty(shape)
    out[0] = e[0]
    for k in range(1, shape[0]):
        out[k] = phi * out[k - 1] + np.sqrt(1 - phi**2) * e[k]
    return out


def _field(rng):
    nt = DATES.size
    base = np.where(COLD, 0.0, 20.0)[None, :, None]
    season = 5 * np.sin(2 * np.pi * np.arange(nt) / 12)[:, None, None]
    x = base + season + 0.3 * _ar1(rng, 0.5, (nt, 1, 1)) + _ar1(rng, 0.3, (nt, LAT.size, LON.size))
    p_gap = 0.15 * (1 - np.arange(nt) / (nt - 1))
    gaps = rng.uniform(size=x.shape) < p_gap[:, None, None]
    x[gaps & COLD[None, :, None]] = np.nan
    x[rng.uniform(size=x.shape) < 0.01] = np.nan
    return xr.DataArray(x, dims=("time", "lat", "lon"), coords={"time": DATES, "lat": LAT, "lon": LON})


def test_fixed_mask_removes_spurious_trend():
    rng = np.random.default_rng(42)
    t = decimal_year(DATES.values)
    out = {"old": [], "fixed": []}
    cold_in_mask = 0
    for _ in range(SIMS):
        da = _field(rng)
        valid = xr.DataArray(has_enough_data(da.notnull().sum("time").values, t), dims=("lat", "lon"),
                             coords={"lat": LAT, "lon": LON})
        old = area_weighted_mean(da, valid).values
        fixed, info = fixed_mask_mean(da)
        assert int(valid.sum()) == 60 and int(info["mask"][~COLD].sum()) == 30  # all cells pass 80%
        cold_in_mask += int(info["mask"][COLD].sum())  # by chance a cold cell can reach 95%
        for k, y in (("old", old), ("fixed", fixed.values)):
            r = trend_report(y, DATES.values)
            out[k].append((r["slope_per_decade"], r["significant"]))
    se = np.sqrt(0.05 * 0.95 / SIMS)
    res = {k: (np.mean([s for s, _ in v]), np.std([s for s, _ in v], ddof=1), np.mean([g for _, g in v]))
           for k, v in out.items()}
    print(f"cold cells that reached 95% and joined the mask: {cold_in_mask} of {30 * SIMS}")
    for k, (m, sd, rate) in res.items():
        print(f"{k:6s}: mean slope {m:+.4f} per decade (SD {sd:.4f}), share significant at 0.05: {rate:.3f}")
    assert res["old"][0] < 0 and res["old"][2] >= 0.8
    assert res["fixed"][2] <= 0.05 + 3 * se
    assert abs(res["fixed"][0]) < 3 * res["fixed"][1] / np.sqrt(SIMS)
