from pathlib import Path

import pytest

from ecodelta_engine.catalog import NOT_FOUND, build_catalog, parse_datasets_md, read_variables_yaml
from ecodelta_engine.load import read_manifest

DATASETS_MD = """
| Product | Short name | Version | Variable (source -> output) | Units | DOI (from metadata) |
|---|---|---|---|---|---|
| MERRA-2 x | M2TMNXSLV | 5.12.4 | `T2M` -> `t2m` | degC | 10.5067/AP1B0BA5PD2K |

- GMAO (2015), MERRA-2 ..., doi:10.5067/AP1B0BA5PD2K
"""


def test_parse_datasets_md(tmp_path):
    p = tmp_path / "DATASETS.md"
    p.write_text(DATASETS_MD)
    d = parse_datasets_md(p)
    assert d == {"t2m": {"product": "MERRA-2 x", "short_name": "M2TMNXSLV", "version": "5.12.4",
                         "doi": "10.5067/AP1B0BA5PD2K", "citation": "GMAO (2015), MERRA-2 ..., doi:10.5067/AP1B0BA5PD2K"}}
    assert parse_datasets_md(tmp_path / "missing.md") == {}


def test_catalog_joins_and_marks_missing_doi(fixture_root):
    cat = build_catalog(read_manifest(fixture_root), {})
    assert sorted(cat) == sorted(read_variables_yaml())
    assert cat["evap"]["land_only"] and cat["evap"]["product"]["doi"] == NOT_FOUND
    assert cat["t2m"]["period"] == ["2001-01", "2025-09"]


def test_catalog_fails_on_missing_entries(fixture_root):
    manifest = read_manifest(fixture_root)
    plain = read_variables_yaml()
    with pytest.raises(ValueError, match="no variables.yaml entry for \\['t2m'\\]"):
        build_catalog(manifest, {}, {k: v for k, v in plain.items() if k != "t2m"})
    with pytest.raises(ValueError, match="not in manifest.json: \\['t2m'\\]"):
        build_catalog({k: v for k, v in manifest.items() if k != "t2m"}, {}, plain)


def test_catalog_fails_on_unit_or_doi_conflict(fixture_root):
    manifest = read_manifest(fixture_root)
    bad = dict(manifest, t2m=dict(manifest["t2m"], units="K"))
    with pytest.raises(ValueError, match="units"):
        build_catalog(bad, {})
    bad = dict(manifest, t2m=dict(manifest["t2m"], source_doi="10.1/a"))
    with pytest.raises(ValueError, match="DOI"):
        build_catalog(bad, {"t2m": {"doi": "10.1/b"}})


def test_real_datasets_md_if_present():
    p = Path(__file__).resolve().parents[2] / "nasa-data" / "docs" / "DATASETS.md"
    if not p.exists():
        pytest.skip("nasa-data/docs/DATASETS.md not present")
    d = parse_datasets_md(p)
    assert set(d) == set(read_variables_yaml())
    assert all(v["doi"].startswith("10.") and v["citation"] != NOT_FOUND for v in d.values())


def test_provenance_is_null_when_the_data_build_has_no_value(fixture_root):
    prov = build_catalog(read_manifest(fixture_root), {})["t2m"]["provenance"]
    assert prov["collection_id"] is None and prov["doi"] is None and prov["source_units"] is None
    assert prov["units"] == "degC" and prov["displayed_units"] == "°C" and prov["period"] == ["2001-01", "2025-09"]
    assert [s["step"] for s in prov["processing_steps"]] == ["unit conversion", "regridding to 2 x 2 degrees"]


def test_provenance_copies_manifest_values(fixture_root):
    manifest = read_manifest(fixture_root)
    real = dict(manifest["t2m"], source_doi="10.5067/X", collection_concept_id="C1-GES_DISC", source_units="K",
                native_resolution={"lon_deg": 0.625}, retrieved={"data_first": "2026-11-14"})
    prov = build_catalog(dict(manifest, t2m=real), {})["t2m"]["provenance"]
    assert (prov["doi"], prov["collection_id"], prov["source_units"]) == ("10.5067/X", "C1-GES_DISC", "K")
    assert prov["native_resolution"] == {"lon_deg": 0.625} and prov["retrieved"] == {"data_first": "2026-11-14"}


def test_held_variables_are_dropped_from_the_real_build(fixture_root):
    from ecodelta_engine.cli import apply_holds
    plain = read_variables_yaml()
    plain = dict(plain, precip=dict(plain["precip"], hold="reason"))
    manifest, kept, held = apply_holds(read_manifest(fixture_root), plain)
    assert held["precip"] == "reason" and "precip" not in manifest and "precip" not in kept
    assert "evap" in manifest and "evap" in kept
