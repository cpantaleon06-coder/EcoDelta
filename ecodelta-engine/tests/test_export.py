import json
import math

import numpy as np
import xarray as xr

from ecodelta_engine.export import LIMITATIONS, SPATIAL_DEPENDENCE, clean, grid_file, rnd, write_json


def test_rnd_significant_digits_and_nan():
    assert rnd(0.271713678) == 0.2717 and rnd(-1.40456) == -1.405 and rnd(8.581125e-39) == 8.581e-39
    assert rnd(float("nan")) is None and rnd(math.inf) is None and rnd(None) is None


def test_clean_converts_numpy_and_is_deterministic(tmp_path):
    obj = {"b": np.float32(0.123456), "a": [np.int64(3), np.bool_(True), np.nan], "c": (1.0, 2)}
    assert clean(obj) == {"b": 0.1235, "a": [3, True, None], "c": [1.0, 2]}
    write_json(tmp_path / "x.json", obj)
    first = (tmp_path / "x.json").read_text()
    write_json(tmp_path / "x.json", dict(reversed(list(obj.items()))))
    assert (tmp_path / "x.json").read_text() == first
    assert list(json.loads(first)) == ["a", "b", "c"]


def test_grid_file_evidence_uses_q_and_ci():
    """Per-cell evidence index into evidence_classes: q replaces p; null where the cell was not tested."""
    q = np.array([0.001, 0.001, 0.03, 0.08, 0.5, np.nan]).reshape(2, 3)
    lo = np.array([0.1, -0.1, 0.1, 0.1, -1, np.nan]).reshape(2, 3)
    ds = xr.Dataset({k: (("lat", "lon"), v) for k, v in {
        "slope": lo + 0.1, "ci_low": lo, "ci_high": lo + 0.3, "pvalue": q / 2, "qvalue": q,
        "significant": q <= 0.05, "n_valid": np.full(q.shape, 297)}.items()},
        coords={"lat": [1.0, 3.0], "lon": [1.0, 3.0, 5.0]})
    g = grid_file("x", {"grid": ds, "units": "K"})
    assert [g["evidence_classes"][c] if c is not None else None for c in g["evidence"]] == \
        ["strong", "weak", "moderate", "weak", "none", None]
    assert g["significant"] == [1, 1, 1, 0, 0, None] and g["evidence_classes"] == ["strong", "moderate", "weak", "none"]


def test_spatial_dependence_statement():
    assert SPATIAL_DEPENDENCE in LIMITATIONS and "0.059 +/- 0.007" in SPATIAL_DEPENDENCE
    assert "independent" in SPATIAL_DEPENDENCE and "target 0.05" in SPATIAL_DEPENDENCE
