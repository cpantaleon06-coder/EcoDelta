"""Named regions as lat/lon boxes, masks, area weights and coverage.

Area weights: on the 2 degree grid (centers -89..89, edges at -90..90) the exact area of a
cell is proportional to sin(lat + 1) - sin(lat - 1) = 2 sin(1 deg) cos(lat), so cos(latitude)
weights are exact; there are no half-width pole rows on this grid.
"""

from pathlib import Path

import numpy as np
import xarray as xr
import yaml

from . import config

KIND = "approximate_box"
DISPLAY_NOTE = "approximate study area, not a political border"


def load_regions(path: Path = config.CATALOG_DIR / "regions.yaml") -> list[dict]:
    regions = yaml.safe_load(path.read_text())
    ids = [r["id"] for r in regions]
    if len(set(ids)) != len(ids):
        raise ValueError(f"duplicate region ids in {path}")
    for r in regions:
        validate_box(r["box"])
        r.setdefault("phrase", r["name"])
        r.update(kind=KIND, display_note=DISPLAY_NOTE)
    return regions


def validate_box(box) -> None:
    lat_min, lat_max, lon_min, lon_max = box
    if not (-90 <= lat_min < lat_max <= 90 and -180 <= lon_min <= 180 and -180 <= lon_max <= 180
            and lon_min != lon_max):
        raise ValueError(f"invalid box {box}: need -90 <= lat_min < lat_max <= 90 and lon in -180..180")


def custom_region(lat_min: float, lat_max: float, lon_min: float, lon_max: float, name: str = "Custom box") -> dict:
    """A user-defined box region (for future use; not part of the web export)."""
    box = [float(lat_min), float(lat_max), float(lon_min), float(lon_max)]
    validate_box(box)
    return {"id": "custom", "name": name, "box": box, "kind": KIND, "display_note": DISPLAY_NOTE}


def box_mask(box, lat: np.ndarray, lon: np.ndarray) -> xr.DataArray:
    """True for cells whose center is inside the box (edges inclusive; lon_min > lon_max crosses 180)."""
    lat_min, lat_max, lon_min, lon_max = box
    la = xr.DataArray(lat, dims="lat", coords={"lat": lat})
    lo = xr.DataArray(lon, dims="lon", coords={"lon": lon})
    in_lon = (lo >= lon_min) & (lo <= lon_max) if lon_min <= lon_max else (lo >= lon_min) | (lo <= lon_max)
    return (la >= lat_min) & (la <= lat_max) & in_lon


def area_weights(lat: np.ndarray) -> np.ndarray:
    return np.cos(np.deg2rad(lat))


def coverage(box_cells: xr.DataArray, valid_cells: xr.DataArray) -> dict:
    """How much of a region box has usable data.

    box_cells: bool (lat, lon), cells inside the box. valid_cells: bool (lat, lon), cells
    that pass the data requirement for this variable. covered_fraction is area-weighted.
    """
    w = xr.DataArray(area_weights(box_cells.lat.values), dims="lat", coords={"lat": box_cells.lat})
    inside = box_cells & valid_cells
    total = float((w * box_cells).sum())
    return {
        "n_box_cells": int(box_cells.sum()),
        "n_valid_cells": int(inside.sum()),
        "covered_fraction": round(float((w * inside).sum()) / total, 4) if total else 0.0,
    }
