import json

import pytest

from ecodelta_engine import quality
from ecodelta_engine.regions import load_regions


def test_pair_takes_worse_status_and_its_reason():
    pub = {"status": "published", "reason": "agrees"}
    held = {"status": "held", "reason": "disagrees"}
    assert quality.pair_quality(pub, held, "a", "b") == {"status": "held", "reason": "b: disagrees"}
    lim = {"status": "limited", "reason": "x"}
    assert quality.pair_quality(lim, lim, "a", "b") == {"status": "limited", "reason": "a: x; b: x"}


def test_fixture_is_limited_and_needs_no_gate_file():
    regions = load_regions()
    q = quality.statuses(quality.load_gate("fixture", ["precip"], regions), ["precip"], regions)
    assert {s["status"] for s in q["precip"].values()} == {"limited"}


def test_real_gate_must_cover_every_pair(tmp_path, monkeypatch):
    regions = load_regions()
    f = tmp_path / "gate.json"
    f.write_text(json.dumps({"pairs": {"precip": {regions[0]["id"]: {"status": "published", "reason": ""}}}}))
    monkeypatch.setattr(quality, "GATE_FILE", f)
    with pytest.raises(ValueError, match="no status"):
        quality.load_gate("real", ["precip"], regions)


def test_committed_gate_covers_every_pair():
    regions = load_regions()
    gate = json.loads(quality.GATE_FILE.read_text())
    quality.load_gate("real", list(gate["pairs"]), regions)
    assert {s["status"] for v in gate["pairs"].values() for s in v.values()} <= set(quality.RANK)
