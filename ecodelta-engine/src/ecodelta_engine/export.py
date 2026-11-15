"""Write web_data/: versioned, schema-checked JSON files that the web app only displays.

Rounding: every float is rounded to 4 significant digits (`rnd`); NaN and infinity become null.
Keys are sorted, so the same inputs give byte-identical files (except meta.build_date and timing).
"""

import json
import math
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import trendkit

from . import __version__, config
from .compute import COMPARE_METHOD, COMPARE_NOTE, Q_NOTE
from .screen import (EVIDENCE_CLASSES, EVIDENCE_DEFINITION, MAGNITUDE_DEFINITION, ORDERINGS, SCORE_DEFINITION,
                     evidence_code)

SCHEMA_VERSION = "1.2.0"
SIG_DIGITS = 4
AUTOCORR_NOTES = {"yue_wang": "Yue and Wang (2004) variance correction with an AR(1) model, floored at 1; "
                              "recommended in trendkit docs/METHODS.md"}

# Figure read from trendkit docs/METHODS.md, section 6 (not recomputed here).
SPATIAL_DEPENDENCE = (
    "Neighbouring grid cells on the trend maps are correlated. The Benjamini-Hochberg false discovery rate "
    "control used on the maps is proven only for independent or positively dependent tests, so here it holds "
    "approximately: a single map can have more or fewer than 5% false discoveries. trendkit's Monte Carlo test "
    "measured a false discovery proportion of 0.059 +/- 0.007 (mean of 40 synthetic maps, target 0.05), but its "
    "synthetic cells were independent of each other, so it does not measure the effect of spatial correlation.")

LIMITATIONS = [
    "Regions are approximate latitude/longitude boxes, not political borders; some boxes overlap.",
    "Each grid cell is 2 x 2 degrees (about 220 km), so local details are not visible.",
    "Temperature comes from a reanalysis (MERRA-2), evapotranspiration, runoff and soil moisture from a land "
    "surface model (GLDAS Noah), and precipitation from a satellite-gauge estimate (GPM IMERG); none is a "
    "direct measurement at every place, and the three sources differ in how they are made.",
    "Trends are monotonic (Mann-Kendall, Sen's slope) over the stated period only; a change that rises and then "
    "falls can show as no significant trend, and a sudden jump (for example a change of satellite) can look "
    "like a trend.",
    "Statistically significant does not mean large or important, and a trend says nothing about its cause.",
    "Regional means average only the cells of a region that have data in at least 95% of the months, the same "
    "cells every month; land-only variables cover only the land part of a region.",
    SPATIAL_DEPENDENCE,
]


def rnd(x, sig: int = SIG_DIGITS):
    """Round to `sig` significant digits; None for NaN, infinity or None."""
    if x is None:
        return None
    x = float(x)
    return float(f"{x:.{sig}g}") if math.isfinite(x) else None


def clean(obj):
    """JSON-ready copy: numpy types to Python, floats rounded with rnd, tuples and arrays to lists."""
    if isinstance(obj, dict):
        return {str(k): clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, np.ndarray)):
        return [clean(v) for v in obj]
    if isinstance(obj, (bool, np.bool_)):
        return bool(obj)
    if isinstance(obj, (int, np.integer)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        return rnd(obj)
    return obj


def write_json(path: Path, obj, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    kw = {"separators": (",", ":")} if compact else {"indent": 1}
    path.write_text(json.dumps(clean(obj), sort_keys=True, ensure_ascii=False, allow_nan=False, **kw) + "\n")


def git_info(path: Path) -> dict:
    """Commit hash and whether the working tree has uncommitted changes; commit None if there is none."""
    def run(*args):
        r = subprocess.run(["git", "-C", str(path), *args], capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else None
    commit = run("rev-parse", "HEAD")
    status = run("status", "--porcelain")
    return {"commit": commit, "uncommitted_changes": bool(status) if status is not None else None}


def axis(values) -> dict:
    v = np.asarray(values, dtype=float)
    return {"first": v[0], "last": v[-1], "step": v[1] - v[0], "n": v.size}


def grid_file(var: str, res: dict) -> dict:
    g = res["grid"]
    tested = g.pvalue.notnull().values.ravel()
    sig = g.significant.values.ravel()
    return {
        "schema_version": SCHEMA_VERSION,
        "variable": var,
        "slope_units": f"{res['units']} per decade",
        "lat": axis(g.lat), "lon": axis(g.lon),
        "order": "row-major: index = i_lat * n_lon + i_lon, lat ascending (south to north), lon ascending",
        "slope": g.slope.values.ravel(),
        "ci_low": g.ci_low.values.ravel(),
        "ci_high": g.ci_high.values.ravel(),
        "p": g.pvalue.values.ravel(),
        "q": g.qvalue.values.ravel(),
        "significant": [int(s) if t else None for s, t in zip(sig, tested)],
        "evidence": [int(c) if t else None for c, t in
                     zip(evidence_code(g.qvalue.values.ravel(), g.ci_low.values.ravel(), g.ci_high.values.ravel()),
                         tested)],
        "evidence_classes": list(EVIDENCE_CLASSES[:4]),
        "n_valid": g.n_valid.values.ravel().astype(int),
    }


def region_file(region: dict, entries: list[dict], results: dict, dates: list[str]) -> dict:
    variables = {}
    for e in entries:
        rr = results[e["variable"]]["regions"][region["id"]]
        variables[e["variable"]] = {
            "rank": e["rank"], "rank_by_magnitude": e["rank_by_magnitude"], "score": e["score"],
            "evidence": e["evidence"], "magnitude": e["magnitude"], "map_cells": rr["map_cells"],
            "answers": e["answers"], "sentence": e["sentence"],
            "cautions": e["cautions"], "report": rr["report"],
            "series": None if rr["anomalies"] is None else
            {"anomaly": rr["anomalies"], "running_mean_12": rr["running_mean"]},
        }
    return {"schema_version": SCHEMA_VERSION, "region": region, "dates": dates, "variables": variables}


def screening_file(region: dict, entries: list[dict]) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "region_id": region["id"],
        "region_file": f"regions/{region['id']}.json",
        "by_evidence": [e["variable"] for e in entries],
        "by_magnitude": [e["variable"] for e in sorted(entries, key=lambda e: e["rank_by_magnitude"])],
        "ranking": [{
            "rank": e["rank"], "rank_by_magnitude": e["rank_by_magnitude"], "variable": e["variable"],
            "name": e["answers"]["what"]["name"], "evidence_class": e["evidence"]["class"],
            "total_change": e["magnitude"]["total_change"],
            "standardized_change": e["magnitude"]["standardized_change"],
            "cells_significant_fraction": e["answers"]["significance"]["cells_significant_after_fdr_fraction"],
            "verdict": e["answers"]["what"]["verdict"], **e["score"],
            "slope_per_decade": e["answers"]["how_much"]["slope_per_decade"],
            "ci_per_decade": e["answers"]["how_much"]["ci_per_decade"],
            "public_unit": e["answers"]["how_much"]["public_unit"],
            "sentence": e["sentence"], "cautions": e["cautions"],
        } for e in entries],
    }


def compare_file(var: dict, pairs: list[dict], period: dict) -> dict:
    return {"schema_version": SCHEMA_VERSION, "variable": var["id"], "units": var["units"],
            "public_unit": var["public_unit"], "period": [period["start"], period["end"]],
            "method": COMPARE_METHOD, "note": COMPARE_NOTE, "q_note": Q_NOTE, "pairs": pairs}


def meta_file(source: str, catalog: dict, period: dict, n_months: int, missing: list[str],
              timing: dict, sanity: dict) -> dict:
    products = {}
    for v in sorted(catalog):
        p = catalog[v]["product"]
        prod = products.setdefault(p["short_name"], {k: p[k] for k in ("name", "short_name", "version", "doi",
                                                                        "citation")} | {"variables": []})
        prod["variables"].append(v)
    lat = np.arange(-89.0, 90.0, 2.0)
    lon = np.arange(-179.0, 180.0, 2.0)
    return {
        "schema_version": SCHEMA_VERSION,
        "build_date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": source,
        "synthetic": source == "fixture",
        "engine": {"version": __version__, **git_info(config.REPO)},
        "trendkit": {"version": trendkit.__version__, **git_info(Path(trendkit.__file__).resolve().parents[2])},
        "period": {"start": period["start"], "end": period["end"], "n_months": n_months,
                   "years": period["years"]},
        "grid": {"resolution_deg": 2.0, "lat": axis(lat), "lon": axis(lon), "cell_reference": "center"},
        "methods": {
            "trend_estimator": "Sen's slope, reported per decade in the variable's units",
            "significance_test": "Mann-Kendall",
            "autocorrelation_handling": config.TREND_METHOD,
            "autocorrelation_note": AUTOCORR_NOTES.get(config.TREND_METHOD, "see trendkit docs/METHODS.md"),
            "alpha": config.ALPHA, "ci_level": 1 - config.ALPHA,
            "fdr": {"method": "Benjamini-Hochberg", "q": config.FDR_Q, "applies_to": "grid cells, per variable",
                    "spatial_dependence": SPATIAL_DEPENDENCE},
            "deseasonalizing": "monthly climatology subtracted per cell and per regional series",
            "climatology_base_period": config.BASE_PERIOD or [period["start"], period["end"]],
            "data_requirement": "at least 10 years of valid months and at least 80% of months valid (trendkit)",
            "regional_mean": ("cos(latitude)-weighted mean over a fixed mask: the cells inside the box with data in at "
                              f"least {config.FIXED_MASK_MIN_VALID:.0%} of the months, the same cells every month; a month "
                              f"is missing when more than {config.FIXED_MASK_MAX_MISSING_WEIGHT:.0%} of the mask's area "
                              "weight has no data" if config.FIXED_MASK else
                              "cos(latitude)-weighted mean of cells inside the box that pass the data requirement"),
            "regional_mean_rule": {"mode": "fixed_mask" if config.FIXED_MASK else "all_valid_cells",
                                   "min_valid_fraction": config.FIXED_MASK_MIN_VALID,
                                   "max_missing_weight": config.FIXED_MASK_MAX_MISSING_WEIGHT},
            "display_series": "monthly anomalies and a trailing 12-month running mean (null until 12 valid months); "
                              "no annual means are published because the last year is incomplete",
            "ranking": SCORE_DEFINITION,
            "evidence_classes": EVIDENCE_DEFINITION,
            "magnitude": MAGNITUDE_DEFINITION,
            "orderings": ORDERINGS,
            "region_comparison": COMPARE_METHOD,
            "rounding": f"every number rounded to {SIG_DIGITS} significant digits",
        },
        "products": list(products.values()),
        "variables_included": sorted(catalog),
        "variables_missing": missing,
        "limitations": (["SYNTHETIC FIXTURE DATA: these numbers are not real observations."]
                        if source == "fixture" else []) + LIMITATIONS,
        "timing": timing,
        "sanity_checks": sanity,
    }


def run_provenance(meta: dict) -> dict:
    """The per-variable provenance fields that describe this build rather than the data."""
    m = meta["methods"]
    return {
        "statistics": {"trendkit_version": meta["trendkit"]["version"],
                       **{k: m[k] for k in ("deseasonalizing", "climatology_base_period", "trend_estimator",
                                            "significance_test", "autocorrelation_handling",
                                            "autocorrelation_note", "alpha", "ci_level", "fdr",
                                            "data_requirement", "regional_mean")}},
        "engine_commit": meta["engine"]["commit"],
        "engine_uncommitted_changes": meta["engine"]["uncommitted_changes"],
        "manifest_sha256": meta["data"]["manifest_sha256"],
    }


def export(out: Path, source: str, catalog: dict, regions: list[dict], results: dict, ranked: dict,
           period: dict, missing: list[str], timing: dict, sanity: dict, manifest_sha256: str | None,
           compare: dict) -> dict:
    """Write every file into a temporary folder, then swap it in place of `out`. Returns size info."""
    tmp = out.with_name(out.name + ".tmp")
    shutil.rmtree(tmp, ignore_errors=True)
    any_res = next(iter(results.values()))
    dates = list(pd.DatetimeIndex(any_res["dates"]).strftime("%Y-%m"))
    included = {v: catalog[v] for v in results}
    meta = meta_file(source, included, period, len(dates), missing, timing, sanity) | {
        "data": {"manifest_sha256": manifest_sha256}}
    included = {v: dict(c, provenance=c["provenance"] | run_provenance(meta)) for v, c in included.items()}
    write_json(tmp / "meta.json", meta)
    write_json(tmp / "catalog.json", {"schema_version": SCHEMA_VERSION,
                                      "variables": [included[v] for v in sorted(included)]})
    write_json(tmp / "regions.json", {"schema_version": SCHEMA_VERSION, "note": LIMITATIONS[0],
                                      "regions": regions})
    for var, res in sorted(results.items()):
        write_json(tmp / "grids" / f"{var}.json", grid_file(var, res), compact=True)
        write_json(tmp / "compare" / f"{var}.json", compare_file(included[var], compare[var], period), compact=True)
    for region in regions:
        entries = ranked[region["id"]]
        write_json(tmp / "regions" / f"{region['id']}.json", region_file(region, entries, results, dates), compact=True)
        write_json(tmp / "screening" / f"{region['id']}.json", screening_file(region, entries))
    shutil.rmtree(out, ignore_errors=True)
    tmp.rename(out)
    sizes = {str(p.relative_to(out)): p.stat().st_size for p in sorted(out.rglob("*.json"))}
    return {"total_bytes": sum(sizes.values()), "n_files": len(sizes),
            "compare_bytes": sum(v for k, v in sizes.items() if k.startswith("compare/")),
            "largest": sorted(sizes.items(), key=lambda kv: -kv[1])[:5]}
