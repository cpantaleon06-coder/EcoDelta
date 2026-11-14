import numpy as np
import pytest
import xarray as xr

from ecodelta_engine.load import LAT, LON
from ecodelta_engine.regions import area_weights, box_mask, coverage, custom_region, load_regions


def test_regions_file():
    regions = load_regions()
    ids = [r["id"] for r in regions]
    assert ids[0] == "global" and len(regions) == 21
    for r in regions:
        assert box_mask(r["box"], LAT, LON).sum() > 0, r["id"]


def test_box_mask_inclusive_and_dateline():
    m = box_mask([-1, 1, -3, 3], LAT, LON)
    assert int(m.sum()) == 2 * 4  # lat centers -1, 1; lon centers -3, -1, 1, 3
    m = box_mask([-1, 1, 177, -177], LAT, LON)  # crosses 180
    assert sorted(m.lon[m.any("lat")].values) == [-179, -177, 177, 179]


def test_custom_region_validates():
    assert custom_region(10, 20, -5, 5)["box"] == [10.0, 20.0, -5.0, 5.0]
    with pytest.raises(ValueError):
        custom_region(20, 10, 0, 5)


def test_area_weights_are_exact_cell_areas():
    edges = np.deg2rad(np.arange(-90, 91, 2))
    exact = np.diff(np.sin(edges))
    w = area_weights(LAT)
    np.testing.assert_allclose(w / w.sum(), exact / exact.sum(), rtol=1e-12)


def test_coverage_counts_and_area_fraction():
    box = box_mask([-90, 90, -180, 180], LAT, LON)
    north = xr.DataArray(LAT > 0, dims="lat", coords={"lat": LAT}) & xr.ones_like(box)
    c = coverage(box, north)
    assert c == {"n_box_cells": 16200, "n_valid_cells": 8100, "covered_fraction": 0.5}
