"""Quality gate v1: per (variable, region) status from the reference comparisons in data/quality/.

Rule fixed 2026-11-15 ~07:15, before the GLDAS vs MERRA-2 land comparison was run; approved by the
owner on 2026-11-15 with G4 on. Inputs: data/quality/*_vs_*.json (scripts/quality/vs_reference.py and
t2m_vs_gistemp.py). Prints the table; with --write also writes data/catalog/quality_gate.json, which
the engine reads for real builds.
Usage (from ecodelta-engine/): .venv/bin/python -I scripts/quality/gate.py [--write]
"""
import json, sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[2]
IN_DIR = ENGINE / "data" / "quality"
OUT = ENGINE / "data" / "catalog" / "quality_gate.json"
INDEPENDENCE_CAP = True  # G4, owner decision 2026-11-15

ALPHA = 0.05
MIN_CHECKED_SHARE = 0.5
RULE = """QUALITY GATE v1, unit = one (variable, region) pair, status = published | limited | held
G0 pipeline: a variable failing any step-1 check (source units, 297 consecutive months, NaN pattern,
   raw-vs-regridded, validate --source real) -> all its pairs held.
G1 data: fixed mask with 0 cells, or valid months < 95% of months -> held ("no data").
G2 reference trend check, fixed primary reference per variable (same cells, common months, anomalies,
   trendkit trend_report on each, D = product - reference via compare_pair, alpha 0.05;
   verdict = increasing / decreasing when p < 0.05, else no clear trend):
     verdicts differ and D significant        -> held     ("disagrees with <ref>")
     verdicts differ, D not significant       -> limited  ("verdict differs from <ref>, difference not significant")
     verdicts equal, D significant            -> limited  ("direction agrees with <ref>, size differs")
     verdicts equal, D not significant        -> published
   soil moisture (reference in other units, no D): verdicts differ -> held; equal -> limited.
   no reference cells in the region         -> limited  ("not checked against a reference")
G3 coverage of the check: reference cells cover < 50% of the product's cells in the region (area)
   -> at most limited ("checked on X% of the region").
G4 independence: reference not independent of the product -> at most limited (owner: on, 2026-11-15).
G5 t2m: nothing published without explicit owner approval (standing rule), whatever the gate says.
G6 region comparisons (compare/<variable>.json): a pair A-B gets the worse status of A and B.
Primary references: t2m GISTEMP v4 250 km land-only (independent, stations);
   precip GPCP v3.3 (related: IMERG Final is calibrated to GPCP); evap, runoff_surface, soil moisture
   MERRA-2 land M2TMNXLND EVLAND / RUNOFF / SFMC (other model and forcing; RUNOFF includes throughflow;
   SFMC is volumetric surface layer)."""

REFS = {  # variable: (json file, reference label, independent, has comparable units)
    "t2m": ("t2m_vs_gistemp.json", "GISTEMP v4 250 km land", True, True),
    "precip": ("precip_vs_gpcp.json", "GPCP v3.3", False, True),
    "evap": ("evap_vs_m2lnd.json", "MERRA-2 land EVLAND", False, True),
    "runoff_surface": ("runoff_vs_m2lnd.json", "MERRA-2 land RUNOFF", False, True),
    "soil_moisture_0_10cm": ("soil_vs_m2lnd.json", "MERRA-2 land SFMC", False, False),
}
RANK = {"published": 0, "limited": 1, "held": 2}


def verdict(s):
    return "no clear trend" if s[3] >= ALPHA else ("increasing" if s[0] > 0 else "decreasing")


def row(o, t2m):
    """Normalise both JSON layouts to (product same cells, reference, diff, reference area fraction)."""
    if t2m:
        return o.get("g250_merra2_same_cells"), o.get("g250"), o.get("g250_diff"), o["g250_mask_area_fraction"]
    return o.get("var_same_cells"), o.get("ref"), o.get("diff"), o["ref_mask_area_fraction"]


def gate(var, o, own_frac, n_cells, valid_share, independence_cap):
    label, indep, units_ok = REFS[var][1:]
    if n_cells == 0 or valid_share < 0.95:
        return "held", "no data in this region", None
    p, r, d, ref_frac = row(o, var == "t2m")
    if r is None:
        return "limited", "not checked against a reference", None
    vp, vr = verdict(p), verdict(r)
    dsig = units_ok and d[3] is not None and d[3] < ALPHA
    if vp != vr and (dsig or not units_ok):
        status, why = "held", f"disagrees with {label}: product {vp}, reference {vr}"
    elif vp != vr:
        status, why = "limited", f"verdict differs from {label} ({vp} vs {vr}), difference not significant"
    elif not units_ok:
        status, why = "limited", f"direction agrees with {label} ({vp}); size not checkable (other units)"
    elif dsig:
        status, why = "limited", f"direction agrees with {label} ({vp}); size differs by {d[0]:+.3f}/decade"
    else:
        status, why = "published", f"agrees with {label} ({vp})"
    share = ref_frac / own_frac if own_frac else 0
    caps = []
    if share < MIN_CHECKED_SHARE:
        caps.append(f"checked on {share:.0%} of the region")
    if independence_cap and not indep:
        caps.append(f"{label} is not independent of the product")
    if caps and status == "published":
        status = "limited"
    return status, "; ".join([why] + caps), (vp, vr, d)


if __name__ == "__main__":
    print(RULE, "\n")
    out = {"version": "1", "rule": RULE, "decision": "approved by the owner 2026-11-15, G4 on",
           "alpha": ALPHA, "min_checked_share": MIN_CHECKED_SHARE, "independence_cap": INDEPENDENCE_CAP,
           "references": {v: {"file": f"data/quality/{r[0]}", "reference": r[1], "independent": r[2]}
                          for v, r in REFS.items()}, "pairs": {}}
    for var, (fname, label, indep, _) in REFS.items():
        res = json.load(open(IN_DIR / fname)); res = res.get("regions", res)
        regions = list(res)
        counts = {True: {}, False: {}}
        print(f"== {var} vs {label} ({'independent' if indep else 'NOT independent'})")
        print(f"{'region':26} {'product':15} {'reference':15} {'D/decade':>9} {'p(D)':>8} {'G4 on':10} {'G4 off':10} reason (applied)")
        for rid in regions:
            o = res[rid]
            if var == "t2m":
                own, n, vs = 1.0, 1, 1.0  # MERRA-2 t2m: full grid, 297/297 months valid (manifest nan_fraction 0)
            else:
                own, n, vs = o["own_mask_area_fraction"], o["own_n_cells"], o["own_valid_month_share"]
            on = gate(var, res[rid], own, n, vs, True)
            off = gate(var, res[rid], own, n, vs, False)
            for k, g in ((True, on), (False, off)):
                counts[k][g[0]] = counts[k].get(g[0], 0) + 1
            g = on if INDEPENDENCE_CAP else off
            out["pairs"].setdefault(var, {})[rid] = {
                "status": g[0], "reason": g[1],
                "product_verdict": g[2][0] if g[2] else None, "reference_verdict": g[2][1] if g[2] else None,
                "difference_per_decade": g[2][2][0] if g[2] and REFS[var][3] else None,
                "difference_p": g[2][2][3] if g[2] and REFS[var][3] else None}
            vp, vr, d = off[2] or ("-", "-", None)
            dd = f"{d[0]:+9.3f} {d[3]:8.1e}" if d and REFS[var][3] else f"{'-':>9} {'-':>8}"
            print(f"{rid:26} {vp:15} {vr:15} {dd} {on[0]:10} {off[0]:10} {(on if INDEPENDENCE_CAP else off)[1]}")
        print(f"counts G4 on: {counts[True]}   G4 off: {counts[False]}\n")
    if "--write" in sys.argv:
        OUT.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
        print("wrote", OUT)
