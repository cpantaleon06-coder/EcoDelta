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
