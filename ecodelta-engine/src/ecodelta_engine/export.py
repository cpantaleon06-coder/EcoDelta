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
from .screen import SCORE_DEFINITION

SCHEMA_VERSION = "1.0.0"
SIG_DIGITS = 4
AUTOCORR_NOTES = {"yue_wang": "Yue and Wang (2004) variance correction with an AR(1) model, floored at 1; "
                              "recommended in trendkit docs/METHODS.md"}

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
    "Regional means average only the cells that pass the data requirement; land-only variables cover only the "
    "land part of a region.",
    "Neighbouring grid cells are correlated, which makes the false discovery rate of a single map more variable "
    "than its 5% target.",
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
        "n_valid": g.n_valid.values.ravel().astype(int),
    }


def region_file(region: dict, entries: list[dict], results: dict, dates: list[str]) -> dict:
    variables = {}
    for e in entries:
        rr = results[e["variable"]]["regions"][region["id"]]
        variables[e["variable"]] = {
            "rank": e["rank"], "score": e["score"], "answers": e["answers"], "sentence": e["sentence"],
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
        "ranking": [{
            "rank": e["rank"], "variable": e["variable"], "name": e["answers"]["what"]["name"],
            "verdict": e["answers"]["what"]["verdict"], **e["score"],
            "slope_per_decade": e["answers"]["how_much"]["slope_per_decade"],
            "ci_per_decade": e["answers"]["how_much"]["ci_per_decade"],
            "public_unit": e["answers"]["how_much"]["public_unit"],
            "sentence": e["sentence"], "cautions": e["cautions"],
        } for e in entries],
    }


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
            "fdr": {"method": "Benjamini-Hochberg", "q": config.FDR_Q, "applies_to": "grid cells, per variable"},
            "deseasonalizing": "monthly climatology subtracted per cell and per regional series",
            "climatology_base_period": config.BASE_PERIOD or [period["start"], period["end"]],
            "data_requirement": "at least 10 years of valid months and at least 80% of months valid (trendkit)",
            "regional_mean": "cos(latitude)-weighted mean of cells inside the box that pass the data requirement",
            "display_series": "monthly anomalies and a trailing 12-month running mean (null until 12 valid months); "
                              "no annual means are published because the last year is incomplete",
            "ranking": SCORE_DEFINITION,
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


def export(out: Path, source: str, catalog: dict, regions: list[dict], results: dict, ranked: dict,
           period: dict, missing: list[str], timing: dict, sanity: dict) -> dict:
    """Write every file into a temporary folder, then swap it in place of `out`. Returns size info."""
    tmp = out.with_name(out.name + ".tmp")
    shutil.rmtree(tmp, ignore_errors=True)
    any_res = next(iter(results.values()))
    dates = list(pd.DatetimeIndex(any_res["dates"]).strftime("%Y-%m"))
    included = {v: catalog[v] for v in results}
    write_json(tmp / "meta.json", meta_file(source, included, period, len(dates), missing, timing, sanity))
    write_json(tmp / "catalog.json", {"schema_version": SCHEMA_VERSION,
                                      "variables": [included[v] for v in sorted(included)]})
    write_json(tmp / "regions.json", {"schema_version": SCHEMA_VERSION, "note": LIMITATIONS[0],
                                      "regions": regions})
    for var, res in sorted(results.items()):
        write_json(tmp / "grids" / f"{var}.json", grid_file(var, res), compact=True)
    for region in regions:
        entries = ranked[region["id"]]
        write_json(tmp / "regions" / f"{region['id']}.json", region_file(region, entries, results, dates), compact=True)
        write_json(tmp / "screening" / f"{region['id']}.json", screening_file(region, entries))
    shutil.rmtree(out, ignore_errors=True)
    tmp.rename(out)
    sizes = {str(p.relative_to(out)): p.stat().st_size for p in sorted(out.rglob("*.json"))}
    return {"total_bytes": sum(sizes.values()), "n_files": len(sizes),
            "largest": sorted(sizes.items(), key=lambda kv: -kv[1])[:5]}
