"""Synthetic stand-in for the data session's processed files.

Writes <root>/data/processed/<variable>.nc plus manifest.json in the exact layout of
nasa-data/scripts/build_coarse_grid.py (`assemble`): dims (time, lat, lon), 2 x 2 degree
grid, first-of-month time stamps, float32, same attribute and manifest keys.

Each series = climatology + seasonal cycle + AR(1) noise (a cell part plus a shared
large-scale part, so regional means are not unrealistically smooth) + planted trends
listed in PLANTED. Land-only variables are NaN over a crude box-shaped land mask and
south of 60S, like GLDAS. Product names and DOIs are deliberately NOT filled in: they
must come from the real manifest and docs/DATASETS.md.

Usage: python -m ecodelta_engine.fixtures [root]
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from . import config

LAT = np.arange(-89.0, 90.0, 2.0)
LON = np.arange(-179.0, 180.0, 2.0)

# Crude continents as (lat_min, lat_max, lon_min, lon_max); synthetic only, not a real land mask.
LAND_BOXES = [
    (15, 72, -168, -55), (60, 83, -73, -12), (7, 20, -105, -77), (-55, 12, -82, -35),
    (36, 71, -10, 40), (-35, 37, -18, 51), (12, 40, 35, 60), (5, 77, 60, 180),
    (-10, 5, 95, 150), (-39, -11, 113, 154), (-90, -63, -180, 180),
]

# Planted trends: variable -> list of (box, change per decade in the variable's units).
# Sahel (+) and Central Africa (-) are neighbouring patches with opposite signs.
PLANTED = {
    "t2m": [((-90, 90, -180, 180), 0.25), ((66.5, 90, -180, 180), 0.6)],
    "precip": [((10, 18, -16, 30), 0.3), ((-4, 6, 10, 30), -0.3)],
    "evap": [((22, 40, 104, 122), 0.08)],
    "runoff_surface": [],  # pure-noise control variable
    "soil_moisture_0_10cm": [((32, 44, -8, 36), -1.5)],
}

# variable -> (units, long_name, land_only)
VARIABLES = {
    "t2m": ("degC", "2 m air temperature, monthly mean", False),
    "precip": ("mm day-1", "precipitation rate, monthly mean", False),
    "evap": ("mm day-1", "evapotranspiration, monthly mean", True),
    "runoff_surface": ("mm day-1", "storm surface runoff, monthly mean", True),
    "soil_moisture_0_10cm": ("kg m-2", "soil moisture content in the 0-10 cm layer, monthly mean", True),
}


def in_box(box, lat=LAT, lon=LON):
    """Boolean (lat, lon) mask of cell centers inside a box."""
    la, lo = np.meshgrid(lat, lon, indexing="ij")
    return (la >= box[0]) & (la <= box[1]) & (lo >= box[2]) & (lo <= box[3])


def land_mask():
    return np.logical_or.reduce([in_box(b) for b in LAND_BOXES])


def ar1(rng, shape, n, phi):
    """AR(1) noise with unit variance, shape (n, *shape)."""
    e = np.empty((n, *shape))
    e[0] = rng.normal(size=shape)
    s = np.sqrt(1 - phi**2)
    for i in range(1, n):
        e[i] = phi * e[i - 1] + s * rng.normal(size=shape)
    return e


def noise(rng, n, phi_cell=0.3, phi_large=0.5, w_large=0.6):
    """Unit-variance noise: independent cell AR(1) plus a shared 20-degree-block AR(1)."""
    large = ar1(rng, (9, 18), n, phi_large).repeat(10, 1).repeat(10, 2)
    return np.sqrt(1 - w_large**2) * ar1(rng, (LAT.size, LON.size), n, phi_cell) + w_large * large


def field(name, times, rng):
    """Synthetic (time, lat, lon) array for one variable, NaN where it has no data."""
    n = len(times)
    years = (np.arange(n) - (n - 1) / 2) / 12  # centered time in years
    season = np.cos(2 * np.pi * (times.month.to_numpy() - 7) / 12)[:, None, None]  # +1 in July
    hemi = np.sign(LAT)[None, :, None]
    alat = np.abs(LAT)[None, :, None]
    eps = noise(rng, n)
    if name == "t2m":
        x = 28 - 45 * (alat / 90) ** 1.5 + (1 + 14 * alat / 90) * hemi * season + (0.6 + 1.2 * alat / 90) * eps
    elif name == "precip":
        base = 1.5 + 5 * np.exp(-((LAT[None, :, None] / 12) ** 2))
        x = base * (1 + 0.3 * hemi * season) + 0.6 * eps
    elif name == "evap":
        base = 0.4 + 2.5 * np.exp(-((LAT[None, :, None] / 25) ** 2))
        x = base * (1 + 0.4 * hemi * season) + 0.15 * eps
    elif name == "runoff_surface":
        x = 0.5 + 0.1 * hemi * season + 0.08 * eps
    else:
        x = 25 - 4 * hemi * season + 2 * eps
    x = np.broadcast_to(x, (n, LAT.size, LON.size)).copy()
    for box, per_decade in PLANTED[name]:
        x += in_box(box)[None] * (per_decade / 10) * years[:, None, None]
    if name != "t2m":
        x = np.clip(x, 0, None)  # rates and storage cannot be negative
    units, _, land_only = VARIABLES[name]
    if land_only:
        x[:, ~(land_mask() & (LAT[:, None] >= -60))] = np.nan
    if name == "precip":
        x[:, np.abs(LAT) > 80] = np.nan  # high-latitude gap, to exercise NaN handling
    gaps = rng.random(x.shape) < 0.01  # 1% scattered missing values
    x[gaps] = np.nan
    return x


def write_fixture(root=config.FIXTURE_DIR, start=config.FIXTURE_START, n_months=config.FIXTURE_MONTHS,
                  seed=2026):
    """Write the synthetic processed files and manifest.json under root; returns the manifest."""
    out = config.processed_dir(Path(root))
    out.mkdir(parents=True, exist_ok=True)
    months = [str(p) for p in pd.period_range(start, periods=n_months, freq="M")]
    times = pd.to_datetime(months)
    manifest = {}
    for k, (name, (units, long_name, _)) in enumerate(VARIABLES.items()):
        x = field(name, times, np.random.default_rng([seed, k]))
        da = xr.DataArray(x.astype("float32"), dims=("time", "lat", "lon"),
                          coords={"time": times, "lat": LAT, "lon": LON})
        da.attrs = dict(units=units, long_name=long_name, source_product="FIXTURE", source_version="0",
                        source_variable=name, source_doi="not found (synthetic fixture)",
                        unit_conversion="none (synthetic)", regridding="none (synthetic)")
        ds = da.to_dataset(name=name)
        ds.attrs = dict(title=f"SYNTHETIC fixture: {long_name}", source="ecodelta_engine.fixtures")
        path = out / f"{name}.nc"
        ds.to_netcdf(path, encoding={name: dict(zlib=True, complevel=4, dtype="float32")})
        manifest[path.name] = dict(
            variable=name, units=units, long_name=long_name, source_product="FIXTURE",
            source_version="0", source_variable=name, source_doi="not found (synthetic fixture)",
            unit_conversion="none (synthetic)", time_range=[months[0], months[-1]], n_months=n_months,
            grid=dict(dims=["time", "lat", "lon"], shape=list(da.shape), resolution_deg=2.0,
                      lat_centers="-89 to 89 step 2", lon_centers="-179 to 179 step 2"),
            native_grid="synthetic", regridding_method="none (synthetic)",
            valid_cells_first_month=int(np.isfinite(x[0]).sum()),
            nan_fraction=round(float(np.isnan(x).mean()), 4))
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


if __name__ == "__main__":
    m = write_fixture(*(sys.argv[1:2] or []))
    print(json.dumps({k: {f: v[f] for f in ("units", "time_range", "valid_cells_first_month", "nan_fraction")}
                      for k, v in m.items()}, indent=1))
