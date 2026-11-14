import json

import pytest

from ecodelta_engine import config
from ecodelta_engine.load import available, open_variable, read_manifest


def test_open_variable_matches_manifest(fixture_root):
    manifest = read_manifest(fixture_root)
    assert set(manifest) == {"t2m", "precip", "evap", "runoff_surface", "soil_moisture_0_10cm"}
    assert available(fixture_root, manifest) == (sorted(manifest), [])
    da = open_variable(fixture_root, manifest["t2m"])
    assert da.shape == (297, 90, 180) and da.dtype == "float64"


def test_units_mismatch_fails_loudly(fixture_root):
    entry = dict(read_manifest(fixture_root)["precip"], units="mm hr-1")
    with pytest.raises(ValueError, match="units attribute"):
        open_variable(fixture_root, entry)


def test_missing_file_is_reported(fixture_root, tmp_path):
    proc = config.processed_dir(tmp_path)
    proc.mkdir(parents=True)
    raw = json.loads((config.processed_dir(fixture_root) / "manifest.json").read_text())
    (proc / "manifest.json").write_text(json.dumps(raw))
    (proc / "t2m.nc").symlink_to(config.processed_dir(fixture_root) / "t2m.nc")
    have, missing = available(tmp_path, read_manifest(tmp_path))
    assert have == ["t2m"] and len(missing) == 4
