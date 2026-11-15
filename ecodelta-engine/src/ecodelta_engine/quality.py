"""Quality gate: a status per (variable, region) and per region comparison.

Real builds read data/catalog/quality_gate.json, written by scripts/quality/gate.py from the reference
comparisons in data/quality/ (rule approved by the owner on 2026-11-15). Held pairs are not exported
as results; they are listed with their reason. The fixture is synthetic, so every pair is "limited".
"""

import json

from . import config

GATE_FILE = config.CATALOG_DIR / "quality_gate.json"
RANK = {"published": 0, "limited": 1, "held": 2}
FIXTURE = {"status": "limited", "reason": "synthetic fixture data; not checked against a reference"}


def load_gate(source: str, variables, regions: list[dict]) -> dict | None:
    """The gate file for a real build (None for the fixture). Every (variable, region) must have a status."""
    if source == "fixture":
        return None
    gate = json.loads(GATE_FILE.read_text())
    missing = [f"{v}/{r['id']}" for v in variables for r in regions if r["id"] not in gate["pairs"].get(v, {})]
    if missing:
        raise ValueError(f"{GATE_FILE} has no status for: {', '.join(missing)}; rerun scripts/quality/gate.py")
    return gate


def statuses(gate: dict | None, variables, regions: list[dict]) -> dict:
    """{variable: {region: {status, reason}}}."""
    return {v: {r["id"]: FIXTURE if gate is None else
                {k: gate["pairs"][v][r["id"]][k] for k in ("status", "reason")} for r in regions}
            for v in variables}


def pair_quality(qa: dict, qb: dict, a: str, b: str) -> dict:
    """G6: a region comparison gets the worse status of its two regions, with that region's reason."""
    status = max(qa["status"], qb["status"], key=RANK.get)
    return {"status": status,
            "reason": "; ".join(f"{rid}: {q['reason']}" for rid, q in ((a, qa), (b, qb)) if q["status"] == status)}


def meta_block(gate: dict | None, q: dict) -> dict:
    held = [{"variable": v, "region": r, "reason": s["reason"]}
            for v in sorted(q) for r, s in q[v].items() if s["status"] == "held"]
    counts = {v: {k: sum(s["status"] == k for s in q[v].values()) for k in RANK} for v in sorted(q)}
    if gate is None:
        return {"version": None, "rule": FIXTURE["reason"], "decision": None, "references": {},
                "counts": counts, "held": held}
    return {"version": gate["version"], "rule": gate["rule"], "decision": gate["decision"],
            "references": {v: gate["references"][v] for v in sorted(q)}, "counts": counts, "held": held}
