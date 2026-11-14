import json

import numpy as np
import pytest
import xarray as xr
from trendkit import area_weighted_mean, trend_report

from ecodelta_engine import config
from ecodelta_engine.fixtures import PLANTED

# Keys written by nasa-data/scripts/build_coarse_grid.py assemble(); the fixture must mirror them.
MANIFEST_KEYS = {"variable", "units", "long_name", "source_product", "source_version", "source_variable",
                 "source_doi", "unit_conversion", "time_range", "n_months", "grid", "native_grid",
                 "regridding_method", "valid_cells_first_month", "nan_fraction"}


@pytest.fixture
def root(fixture_root):
    return fixture_root


def test_structure_matches_processed_files(root):
    proc = config.processed_dir(root)
    manifest = json.loads((proc / "manifest.json").read_text())
    assert set(manifest) == {f"{v}.nc" for v in PLANTED}
    for fname, entry in manifest.items():
        assert set(entry) == MANIFEST_KEYS
        da = xr.open_dataset(proc / fname)[entry["variable"]]
        assert da.dims == ("time", "lat", "lon") and da.shape == (297, 90, 180)
        assert da.lat[0] == -89 and da.lat[-1] == 89 and da.lon[0] == -179 and da.lon[-1] == 179
        assert str(da.time[0].values)[:7] == "2001-01" and str(da.time[-1].values)[:7] == "2025-09"
        assert da.attrs["units"] == entry["units"]


def test_land_only_variables_are_nan_over_ocean_and_south_of_60s(root):
    da = xr.open_dataset(config.processed_dir(root) / "evap.nc")["evap"]
    assert da.sel(lat=slice(-89, -61)).isnull().all()
    assert da.sel(lat=1, lon=-139).isnull().all()  # central Pacific
    assert da.sel(lat=-61, lon=-139).isnull().all()


@pytest.mark.parametrize("var,box,expected", [
    ("precip", (10, 18, -16, 30), 0.3),
    ("precip", (-4, 6, 10, 30), -0.3),
    ("soil_moisture_0_10cm", (32, 44, -8, 36), -1.5),
])
def test_planted_trends_are_recovered(root, var, box, expected):
    da = xr.open_dataset(config.processed_dir(root) / f"{var}.nc")[var]
    r = trend_report(area_weighted_mean(da, box).values, da.time.values)
    assert r["significant"]
    assert r["ci_low_per_decade"] <= expected <= r["ci_high_per_decade"]
