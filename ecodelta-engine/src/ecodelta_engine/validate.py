"""Check an exported web_data folder: JSON Schemas, internal consistency, and golden numbers.

Golden test: for a few grid cells and a few regions, the exported numbers must equal (after the
documented rounding) the same statistics recomputed here by calling trendkit directly on the
processed NetCDF files, without any engine code in between except file loading and region masks.
"""

import json
from pathlib import Path

import jsonschema
import numpy as np
import xarray as xr
from trendkit import area_weighted_mean, deseasonalize_monthly, fixed_mask_mean, mann_kendall, sens_slope, trend_report
from trendkit.grid import has_enough_data
from trendkit.timeutil import decimal_year

from . import config
from .cli import source_root
from .export import rnd
from .load import open_variable, read_manifest
from .regions import box_mask
from .screen import EVIDENCE_CLASSES, evidence_code

GOLDEN_REGIONS = ("global", "sahel", "arctic", "mediterranean")
N_GOLDEN_CELLS = 5


def check_schemas(out: Path) -> list[str]:
    errors = []
    kinds = {"meta.json": "meta", "catalog.json": "catalog", "regions.json": "regions"}
    files = [(p, kinds.get(p.name) or {"grids": "grid", "regions": "region", "screening": "screening", "compare": "compare"}[p.parent.name])
             for p in sorted(out.rglob("*.json"))]
    schemas = {k: json.loads((config.SCHEMA_DIR / f"{k}.schema.json").read_text()) for k in set(k for _, k in files)}
    for path, kind in files:
        for e in jsonschema.Draft202012Validator(schemas[kind]).iter_errors(json.loads(path.read_text())):
            errors.append(f"{path.relative_to(out)}: {e.json_path}: {e.message[:200]}")
    return errors


def check_consistency(out: Path, meta: dict) -> list[str]:
    errors = []
    regions = json.loads((out / "regions.json").read_text())["regions"]
    for v in meta["variables_included"]:
        g = json.loads((out / "grids" / f"{v}.json").read_text())
        n = g["lat"]["n"] * g["lon"]["n"]
        for k in ("slope", "ci_low", "ci_high", "p", "q", "significant", "n_valid"):
            if len(g[k]) != n:
                errors.append(f"grids/{v}.json: {k} has {len(g[k])} values, expected {n}")
        for s, q, p in zip(g["significant"], g["q"], g["p"]):
            if (s is None) != (p is None) or (s is not None and bool(s) != (q <= meta["methods"]["fdr"]["q"])):
                errors.append(f"grids/{v}.json: significant flag disagrees with q")
                break
        cf = json.loads((out / "compare" / f"{v}.json").read_text())
        if len(cf["pairs"]) != len(regions) * (len(regions) - 1) // 2:
            errors.append(f"compare/{v}.json: {len(cf['pairs'])} pairs for {len(regions)} regions")
        for e in cf["pairs"]:
            if (e["verdict"] == "trends differ") != (e["pvalue"] is not None and e["pvalue"] < meta["methods"]["alpha"]):
                errors.append(f"compare/{v}.json {e['region_a']}-{e['region_b']}: verdict disagrees with p")
                break
    for r in regions:
        rf = json.loads((out / "regions" / f"{r['id']}.json").read_text())
        sc = json.loads((out / "screening" / f"{r['id']}.json").read_text())
        if [e["variable"] for e in sorted(sc["ranking"], key=lambda e: e["rank"])] != \
                sorted(rf["variables"], key=lambda v: rf["variables"][v]["rank"]) or \
                sc["by_evidence"] != [e["variable"] for e in sc["ranking"]]:
            errors.append(f"screening/{r['id']}.json: ranking disagrees with regions/{r['id']}.json or by_evidence")
        if sc["by_magnitude"] != sorted(rf["variables"], key=lambda v: rf["variables"][v]["rank_by_magnitude"]):
            errors.append(f"screening/{r['id']}.json: by_magnitude disagrees with rank_by_magnitude")
        for v, d in rf["variables"].items():
            rep = d["report"]
            if rep and rep["verdict"] != "insufficient data" and not d["evidence"]["capped_by_coverage"]:
                want = EVIDENCE_CLASSES[int(evidence_code(rep["pvalue"], rep["ci_low_per_decade"],
                                                          rep["ci_high_per_decade"]))]
                if want != d["evidence"]["class"]:
                    errors.append(f"regions/{r['id']}.json {v}: evidence class {d['evidence']['class']} != {want}")
        for v, d in rf["variables"].items():
            if d["series"] and len(d["series"]["anomaly"]) != len(rf["dates"]):
                errors.append(f"regions/{r['id']}.json: {v} series length != number of dates")
    return errors


def golden(out: Path, root: Path, meta: dict) -> tuple[int, list[str]]:
    """Recompute grid cells and regional reports with trendkit directly; return (n_checked, errors)."""
    errors, n = [], 0
    manifest = read_manifest(root)
    method, alpha = meta["methods"]["autocorrelation_handling"], meta["methods"]["alpha"]
    base = meta["methods"]["climatology_base_period"]
    base = None if base == [meta["period"]["start"], meta["period"]["end"]] else base
    regions = {r["id"]: r for r in json.loads((out / "regions.json").read_text())["regions"]}
    rule = meta["methods"].get("regional_mean_rule", {"mode": "all_valid_cells"})
    for v in meta["variables_included"]:
        da = open_variable(root, manifest[v])
        dates, t = da.time.values, decimal_year(da.time.values)
        g = json.loads((out / "grids" / f"{v}.json").read_text())
        n_lon = g["lon"]["n"]
        tested = [i for i, p in enumerate(g["p"]) if p is not None]
        for k in np.random.default_rng(0).choice(tested, min(N_GOLDEN_CELLS, len(tested)), replace=False):
            i, j = divmod(int(k), n_lon)
            y, _ = deseasonalize_monthly(da.values[:, i, j], dates, base)
            mk = mann_kendall(y, method)
            ss = sens_slope(y, t, alpha, var_s=mk["var_s"])
            want = {"slope": 10 * ss["slope"], "ci_low": 10 * ss["ci_low"], "ci_high": 10 * ss["ci_high"],
                    "p": mk["pvalue"]}
            for key, val in want.items():
                n += 1
                if rnd(val) != g[key][k]:
                    errors.append(f"grids/{v}.json cell ({float(da.lat[i])}, {float(da.lon[j])}) {key}: "
                                  f"exported {g[key][k]} != recomputed {rnd(val)}")
        valid = xr.DataArray(has_enough_data(np.array(g["n_valid"]).reshape(da.shape[1:]), t),
                             dims=("lat", "lon"), coords={"lat": da.lat, "lon": da.lon})
        golden_anomalies = {}
        for rid in GOLDEN_REGIONS:
            if rid not in regions:
                continue
            exported = json.loads((out / "regions" / f"{rid}.json").read_text())["variables"][v]
            box = box_mask(regions[rid]["box"], da.lat.values, da.lon.values)
            if rule["mode"] == "fixed_mask":
                series, fm = fixed_mask_mean(da, box, rule["min_valid_fraction"], rule["max_missing_weight"])
                mask = fm["mask"]
            else:
                mask = box & valid
                series = area_weighted_mean(da, mask) if mask.any() else None
            if not mask.any():
                n += 1
                if exported["report"] is not None:
                    errors.append(f"regions/{rid}.json {v}: report exported for a region without valid cells")
                continue
            series = series.values
            rep = trend_report(series, dates, method=method, alpha=alpha) if base is None else None
            anomalies, _ = deseasonalize_monthly(series, dates, base)
            golden_anomalies[rid] = anomalies
            checks = {"anomaly[:24]": ([rnd(x) for x in anomalies[:24]], exported["series"]["anomaly"][:24])}
            if rep is not None:
                for key in ("slope_per_decade", "ci_low_per_decade", "ci_high_per_decade", "pvalue"):
                    checks[key] = (rnd(rep[key]), exported["report"][key])
                checks["verdict"] = (rep["verdict"], exported["report"]["verdict"])
            for key, (want, got) in checks.items():
                n += 1
                if want != got:
                    errors.append(f"regions/{rid}.json {v} {key}: exported {got} != recomputed {want}")
        # region comparison: D = A - B recomputed from the trendkit regional anomalies above
        pairs = {(e["region_a"], e["region_b"]): e
                 for e in json.loads((out / "compare" / f"{v}.json").read_text())["pairs"]}
        for (a, b), e in pairs.items():
            if a in golden_anomalies and b in golden_anomalies:
                rep = trend_report(golden_anomalies[a] - golden_anomalies[b], dates, method=method, alpha=alpha,
                                   deseasonalize=False)
                verdict = "insufficient data" if rep["verdict"] == "insufficient data" else \
                    "trends differ" if rep["significant"] else "no evidence that trends differ"
                ok = verdict != "insufficient data"
                want = {"difference_slope_per_decade": rnd(rep["slope_per_decade"]) if ok else None,
                        "pvalue": rnd(rep["pvalue"]) if ok else None, "verdict": verdict}
                for key, w in want.items():
                    n += 1
                    if w != e[key]:
                        errors.append(f"compare/{v}.json {a}-{b} {key}: exported {e[key]} != recomputed {w}")
    return n, errors


def check_difference_series(out: Path, meta: dict) -> tuple[int, list[str]]:
    """Rebuild D = A - B from the exported series.anomaly of the two region files, run trend_report, and
    compare with the exported compare record. The web app draws this rebuilt D, so it must agree.

    The anomalies are exported rounded to 4 significant digits, so numbers agree up to that rounding:
    slope and CI ends within 1% of the CI width, p within 0.01, and the same verdict unless the exported
    p is within 0.01 of alpha.
    """
    errors, n = [], 0
    files = {}
    region = lambda rid: files.setdefault(rid, json.loads((out / "regions" / f"{rid}.json").read_text()))
    alpha = meta["methods"]["alpha"]
    for v in meta["variables_included"]:
        for e in json.loads((out / "compare" / f"{v}.json").read_text())["pairs"]:
            A, B = region(e["region_a"]), region(e["region_b"])
            sa, sb = A["variables"][v]["series"], B["variables"][v]["series"]
            if sa is None or sb is None:
                continue
            n += 1
            where = f"compare/{v}.json {e['region_a']}-{e['region_b']}"
            values = lambda s: np.array([np.nan if x is None else x for x in s["anomaly"]], dtype=float)
            dates = np.array([np.datetime64(f"{d}-01") for d in A["dates"]], dtype="datetime64[ns]")
            rep = trend_report(values(sa) - values(sb), dates, method=config.TREND_METHOD, alpha=alpha,
                               deseasonalize=False)
            ok = rep["verdict"] != "insufficient data"
            verdict = ("trends differ" if rep["significant"] else "no evidence that trends differ") if ok \
                else "insufficient data"
            if verdict != e["verdict"] and not (e["pvalue"] is not None and abs(e["pvalue"] - alpha) < 0.01):
                errors.append(f"{where}: verdict from the exported series {verdict!r} != {e['verdict']!r}")
                continue
            if not ok or e["difference_slope_per_decade"] is None:
                continue
            lo, hi = e["difference_ci_per_decade"]
            tol = 0.01 * (hi - lo)
            got = (rep["slope_per_decade"], rep["ci_low_per_decade"], rep["ci_high_per_decade"])
            if any(abs(g - w) > tol for g, w in zip(got, (e["difference_slope_per_decade"], lo, hi))) or \
                    abs(rep["pvalue"] - e["pvalue"]) > 0.01:
                errors.append(f"{where}: rebuilt D gives slope {got[0]:.4g} [{got[1]:.4g}, {got[2]:.4g}] "
                              f"p {rep['pvalue']:.3g}, exported {e['difference_slope_per_decade']} [{lo}, {hi}] "
                              f"p {e['pvalue']}")
    return n, errors


def validate(source: str) -> int:
    out = config.OUTPUT_DIRS[source]
    meta = json.loads((out / "meta.json").read_text())
    errors = check_schemas(out)
    print(f"schemas: {len(list(out.rglob('*.json')))} files, {len(errors)} errors")
    c = check_consistency(out, meta)
    print(f"consistency: {len(c)} errors")
    n_d, diff = check_difference_series(out, meta)
    print(f"difference series: {n_d} pairs rebuilt from the exported region series, {len(diff)} mismatches")
    n, gold = golden(out, source_root(source), meta)
    print(f"golden: {n} numbers recomputed with trendkit, {len(gold)} mismatches")
    for e in errors + c + diff + gold:
        print("  ", e)
    return 0 if not (errors or c or diff or gold) else 1
