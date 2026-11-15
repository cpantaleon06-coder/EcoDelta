"""Apply trend tests to xarray grids and compute area-weighted regional means."""

import numpy as np
import xarray as xr

from .fdr import fdr_bh
from .mannkendall import DEFAULT_METHOD, mann_kendall, sens_slope
from .seasonal import deseasonalize_monthly
from .timeutil import decimal_year, require_increasing

MIN_YEARS = 10  # at least 10 years of valid data ...
MIN_VALID_FRACTION = 0.8  # ... and at least 80% of time steps valid


def has_enough_data(n_valid, t):
    """True where a series meets the minimum data requirement.

    Rule: n_valid * (median time step) >= MIN_YEARS years, and
    n_valid >= MIN_VALID_FRACTION * len(t). For monthly data this means at
    least 120 valid months; for annual data at least 10 valid years.
    """
    step = np.median(np.diff(t)) if len(t) > 1 else np.nan
    return (n_valid * step >= MIN_YEARS) & (n_valid >= MIN_VALID_FRACTION * len(t))


def grid_trends(da, deseasonalize=True, method=DEFAULT_METHOD, alpha=0.05, q=0.05,
                base_period=None, chunk=250):
    """Trend of every grid cell: Sen's slope, Mann-Kendall p-value, and FDR control.

    Per cell (series along time):
        slope       = Sen's slope, converted to units per decade (x 10)
        CI          = Sen's rank-based CI at level 1 - alpha, using the Var(S) of `method`
        p-value     = Mann-Kendall test with `method` (default: Yue-Wang AR(1) correction)
    Across cells:
        q-value     = Benjamini-Hochberg adjusted p-value over all tested cells
        significant = q-value <= q

    Parameters
    ----------
    da : xarray.DataArray with a "time" dimension (datetime64) plus spatial dims,
        typically (time, lat, lon). NaN = missing (for example ocean or land cells).
    deseasonalize : bool. Subtract the monthly climatology first (see
        `deseasonalize_monthly`). Turn off for annual data.
    method : Mann-Kendall variant, see `mann_kendall`.
    alpha : float. Per-cell CI level is 1 - alpha.
    q : float. Target false discovery rate across the map.
    base_period : (start, end) for the climatology, or None for the full record.
    chunk : int. Cells processed per batch; memory use is about
        chunk * n_time^2 * 40 bytes (about 0.9 GB at chunk=250, n_time=300).

    Returns
    -------
    xarray.Dataset on the spatial dims of `da` with variables
        slope, ci_low, ci_high (units of `da` per decade), pvalue, qvalue,
        significant (bool), n_valid (int).
    Cells that fail the minimum data requirement (`has_enough_data`) get NaN
    statistics, significant=False, and are left out of the FDR count.

    Assumptions: equally spaced time steps (monthly or annual), at most one value
    per time step, and series that are independent of each other or positively
    correlated (needed by Benjamini-Hochberg).
    """
    da = da.transpose("time", ...)
    dates = da["time"].values
    t = require_increasing(decimal_year(dates))
    values = da.values.astype(float)
    if deseasonalize:
        values, _ = deseasonalize_monthly(values, dates, base_period)
    space = values.shape[1:]
    Y = values.reshape(len(t), -1).T  # (cells, time)
    n_valid = (~np.isnan(Y)).sum(-1)

    stats = {k: np.full(Y.shape[0], np.nan) for k in ("slope", "ci_low", "ci_high", "pvalue")}
    rows = np.flatnonzero(has_enough_data(n_valid, t))
    for start in range(0, rows.size, chunk):
        r = rows[start : start + chunk]
        mk = mann_kendall(Y[r], method)
        ss = sens_slope(Y[r], t, alpha, var_s=mk["var_s"])
        stats["pvalue"][r] = mk["pvalue"]
        for k in ("slope", "ci_low", "ci_high"):
            stats[k][r] = 10 * ss[k]  # per year -> per decade
    stats["qvalue"], stats["significant"] = fdr_bh(stats["pvalue"], q)
    stats["n_valid"] = n_valid

    template = da.isel(time=0, drop=True)
    per_decade = f"{da.attrs['units']} per decade" if "units" in da.attrs else "per decade"
    ds = xr.Dataset({k: xr.DataArray(v.reshape(space), coords=template.coords, dims=template.dims)
                     for k, v in stats.items()})
    for k in ("slope", "ci_low", "ci_high"):
        ds[k].attrs["units"] = per_decade
    ds.attrs.update(method=method, alpha=alpha, fdr_q=q, deseasonalized=int(deseasonalize),
                    min_years=MIN_YEARS, min_valid_fraction=MIN_VALID_FRACTION)
    return ds


def _region_mask(da, region, lat, lon):
    """Bool DataArray on (lat, lon): True inside `region` (see area_weighted_mean)."""
    if region is None:
        return xr.ones_like(da[lat] * da[lon], dtype=bool)
    if isinstance(region, xr.DataArray):
        inside = region.astype(bool)
    else:
        lat_min, lat_max, lon_min, lon_max = region
        in_lat = (da[lat] >= lat_min) & (da[lat] <= lat_max)
        if lon_min <= lon_max:
            in_lon = (da[lon] >= lon_min) & (da[lon] <= lon_max)
        else:
            in_lon = (da[lon] >= lon_min) | (da[lon] <= lon_max)
        inside = in_lat & in_lon
    if not inside.any():
        raise ValueError("region contains no grid cells")
    return inside


def area_weighted_mean(da, region=None, lat="lat", lon="lon"):
    """Reduce a gridded field to one time series, weighting cells by cos(latitude).

    Formula, at each time step, over the cells in the region that are not NaN:
        mean = sum(w * x) / sum(w),   w = cos(latitude in radians)
    cos(latitude) is proportional to the area of a cell on a regular lat-lon grid.

    Parameters
    ----------
    da : xarray.DataArray with latitude and longitude dims (plus time or others).
    region : None (whole grid); a bounding box (lat_min, lat_max, lon_min, lon_max)
        in the grid's own longitude convention, inclusive, where lon_min > lon_max
        means the box crosses the dateline / grid seam; or a boolean DataArray on
        (lat, lon) that is True inside the region.
    lat, lon : names of the latitude and longitude dims.

    Returns
    -------
    xarray.DataArray without the lat/lon dims. NaN at time steps where the region
    has no valid cell.

    Assumptions: regular lat-lon grid. If cells drop in and out of the record over
    time (for example sea ice or cloud gaps), the regional mean can show a spurious
    trend from the changing sample, not from the data. `fixed_mask_mean` avoids this.
    """
    if region is not None:
        da = da.where(_region_mask(da, region, lat, lon))
    weights = np.cos(np.deg2rad(da[lat])).clip(min=0)
    return da.weighted(weights).mean((lat, lon), skipna=True).where(da.notnull().any((lat, lon)))


def fixed_mask_mean(da, region=None, min_valid_fraction=0.95, max_missing_weight=0.05,
                    lat="lat", lon="lon"):
    """Area-weighted regional mean over the SAME cells at every time step.

    Rule:
        mask     = cells in the region with a value in >= min_valid_fraction of time steps
        share(t) = sum(w over mask cells with a value at t) / sum(w over mask)
        mean(t)  = sum(w * x) / sum(w) over mask cells with a value at t,
                   NaN when 1 - share(t) > max_missing_weight
    with w = cos(latitude). Cells outside the mask are never used, so the regional
    series cannot gain a trend from cells entering or leaving the record; the
    remaining gaps are at most max_missing_weight of the mask's weight per time step.

    Parameters
    ----------
    da : xarray.DataArray with a time dim plus `lat` and `lon` dims.
    region : as in `area_weighted_mean`.
    min_valid_fraction : float in (0, 1]. Share of time steps a cell needs to join the mask.
    max_missing_weight : float in [0, 1). Largest missing share of the mask's weight
        at which a time step still gets a value.

    Returns
    -------
    series : xarray.DataArray without the lat/lon dims (NaN where the rule says missing,
        all NaN when the mask is empty).
    info : dict with mask (bool DataArray on lat, lon), n_cells, region_area_fraction
        (mask weight / region weight), weight_share (ndarray per time step), n_valid
        (time steps with a value), n_total, weight_share_min, weight_share_max (None
        when the mask is empty).

    Limit: cells with frequent gaps (for example seasonal sea ice) are left out, so the
    result describes only the masked part of the region; report region_area_fraction.
    """
    inside = _region_mask(da, region, lat, lon)
    time_dims = [d for d in da.dims if d not in (lat, lon)]
    has = da.notnull()
    mask = inside & (has.mean(time_dims) >= min_valid_fraction)
    cos = np.cos(np.deg2rad(da[lat])).clip(min=0)
    w = cos * mask
    total = float(w.sum())
    n_total = int(np.prod([da.sizes[d] for d in time_dims]))
    if total == 0:
        return (da.isel({lat: 0, lon: 0}, drop=True) * np.nan,
                {"mask": mask, "n_cells": 0, "region_area_fraction": 0.0, "weight_share": np.zeros(n_total),
                 "n_valid": 0, "n_total": n_total, "weight_share_min": None, "weight_share_max": None})
    w_have = (w * has).sum((lat, lon))
    share = w_have / total
    mean = (da.fillna(0) * w).sum((lat, lon)) / w_have.where(w_have > 0)
    series = mean.where(1 - share <= max_missing_weight + 1e-12)  # tolerance: float rounding of share
    s = share.values.ravel()
    return series, {"mask": mask, "n_cells": int(mask.sum()),
                    "region_area_fraction": total / float((cos * inside).sum()),
                    "weight_share": s, "n_valid": int(series.notnull().sum()), "n_total": n_total,
                    "weight_share_min": float(s.min()), "weight_share_max": float(s.max())}
