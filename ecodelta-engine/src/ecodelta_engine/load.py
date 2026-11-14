"""Read the processed NetCDF files and check them against manifest.json."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from . import config

LAT = np.arange(-89.0, 90.0, 2.0)
LON = np.arange(-179.0, 180.0, 2.0)


def read_manifest(root: Path) -> dict:
    """manifest.json re-keyed by variable name: {variable: entry}."""
    path = config.processed_dir(root) / "manifest.json"
    if not path.exists():
        raise FileNotFoundError(f"no manifest at {path}; is the data download finished?")
    raw = json.loads(path.read_text())
    return {entry["variable"]: dict(entry, file=fname) for fname, entry in sorted(raw.items())}


def available(root: Path, manifest: dict) -> tuple[list[str], list[str]]:
    """(variables whose file exists, variables listed in the manifest but missing on disk)."""
    proc = config.processed_dir(root)
    have = [v for v, e in manifest.items() if (proc / e["file"]).exists()]
    return have, [v for v in manifest if v not in have]


def open_variable(root: Path, entry: dict) -> xr.DataArray:
    """Load one variable as float64 (time, lat, lon) and fail loudly on any mismatch with its manifest entry."""
    path = config.processed_dir(root) / entry["file"]
    with xr.open_dataset(path) as ds:
        da = ds[entry["variable"]].load().astype("float64")
    problems = []
    if da.dims != ("time", "lat", "lon"):
        problems.append(f"dims {da.dims} != ('time', 'lat', 'lon')")
    if list(da.shape) != entry["grid"]["shape"]:
        problems.append(f"shape {list(da.shape)} != manifest {entry['grid']['shape']}")
    if not (np.array_equal(da.lat.values, LAT) and np.array_equal(da.lon.values, LON)):
        problems.append("lat/lon axes are not the 2 degree grid (centers -89..89, -179..179)")
    if da.attrs.get("units") != entry["units"]:
        problems.append(f"units attribute {da.attrs.get('units')!r} != manifest {entry['units']!r}")
    months = pd.DatetimeIndex(da.time.values).strftime("%Y-%m")
    if [months[0], months[-1]] != entry["time_range"] or len(months) != entry["n_months"]:
        problems.append(f"time {months[0]}..{months[-1]} ({len(months)}) != manifest "
                        f"{entry['time_range']} ({entry['n_months']})")
    expected = pd.period_range(entry["time_range"][0], entry["time_range"][1], freq="M").strftime("%Y-%m")
    if list(months) != list(expected):
        problems.append("time steps are not consecutive months")
    if problems:
        raise ValueError(f"{path}: " + "; ".join(problems))
    return da
