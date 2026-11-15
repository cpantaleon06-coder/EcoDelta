"""Exported variable vs a reference series fetched by nasa-data/scripts/fetch_reference.py, per region.

Run from ecodelta-engine/ with ECODELTA_DATA_DIR set (references come from nasa-data/scripts/fetch_reference.py).
Usage: vs_reference.py <engine variable> <interim reference dir> <ref var name> <out.json>
Common period = months where every reference file exists. Per region: mask = engine fixed-mask rule on the
reference in the box; both averaged over that mask; deseasonalized over the common period; trendkit
trend_report on each; D = variable - reference tested with engine compute.compare_pair; descriptive OLS step
in D at 2011-01. Also the exported full-box result on the common period.
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd, xarray as xr
from trendkit import deseasonalize_monthly, fixed_mask_mean, trend_report
from trendkit.timeutil import decimal_year
from ecodelta_engine import config
from ecodelta_engine.compute import compare_pair
from ecodelta_engine.load import open_variable, read_manifest
from ecodelta_engine.regions import box_mask, load_regions

var, ref_dir, ref_var, out_path = sys.argv[1:5]
v = open_variable(config.DATA_DIR, read_manifest(config.DATA_DIR)[var])
months = pd.DatetimeIndex(v.time.values).strftime("%Y-%m")
have = [m for m in months if (Path(ref_dir) / f"{m}.nc").exists()]
assert have == list(months[: len(have)]), "reference months must be a contiguous start of the period"
v = v.isel(time=slice(0, len(have)))
dates = v.time.values
ref = xr.concat([xr.open_dataset(Path(ref_dir) / f"{m}.nc")[ref_var] for m in have], dim="time")
ref = ref.assign_coords(time=dates, lat=v.lat, lon=v.lon).astype(float)
t = decimal_year(dates)
seg2 = pd.DatetimeIndex(dates) >= "2011-01-01"
X = np.column_stack([np.ones_like(t), t - t.mean(), seg2.astype(float)])
rule = (config.FIXED_MASK_MIN_VALID, config.FIXED_MASK_MAX_MISSING_WEIGHT)

def trend(an):
    r = trend_report(an, dates, deseasonalize=False)
    return None if r["verdict"] == "insufficient data" else \
        [r["slope_per_decade"], r["ci_low_per_decade"], r["ci_high_per_decade"], r["pvalue"]]

out = {"period": [have[0], have[-1]], "n_months": len(have), "regions": {}}
for r in load_regions():
    box = box_mask(r["box"], v.lat.values, v.lon.values)
    full, finfo = fixed_mask_mean(v, box, *rule)
    row = {"exported_box_same_period": trend(deseasonalize_monthly(full.values, dates)[0]) if finfo["n_cells"] else None,
           "own_mask_area_fraction": round(finfo["region_area_fraction"], 3), "own_n_cells": int(finfo["n_cells"]),
           "own_valid_month_share": finfo["n_valid"] / finfo["n_total"]}
    rs, info = fixed_mask_mean(ref, box, *rule)
    row["ref_mask_area_fraction"] = round(info["region_area_fraction"], 3)
    if info["n_cells"]:
        vs, _ = fixed_mask_mean(v, info["mask"], *rule)
        a, b = deseasonalize_monthly(vs.values, dates)[0], deseasonalize_monthly(rs.values, dates)[0]
        cp = compare_pair(a, b, dates)
        ok = np.isfinite(a - b)
        row |= {"var_same_cells": trend(a), "ref": trend(b),
                "diff": [cp["difference_slope_per_decade"], *(cp["difference_ci_per_decade"] or [None, None]),
                         cp["pvalue"], cp["verdict"]],
                "step_2011": float(np.linalg.lstsq(X[ok], (a - b)[ok], rcond=None)[0][2]),
                "anomaly_correlation": float(np.corrcoef(a[ok], b[ok])[0, 1])}
    out["regions"][r["id"]] = row
json.dump(out, open(out_path, "w"), indent=1, default=float)
f = lambda x: "       n/a        " if x is None else f"{x[0]:+.3f}[{x[1]:+.3f},{x[2]:+.3f}]"
print(f"{var} vs {ref_dir.rstrip('/').split('/')[-1]}:{ref_var}, {have[0]}..{have[-1]} ({len(have)} months)")
print(f"{'region':26s} {'area':>5s} {'var same cells':>22s} {'reference':>22s} {'difference':>22s} {'p':>8s} {'r':>5s} {'step':>6s}  verdict")
for rid, o in out["regions"].items():
    if "diff" not in o:
        print(f"{rid:26s} {o['ref_mask_area_fraction']:5.2f}  no reference cells"); continue
    d = o["diff"]
    print(f"{rid:26s} {o['ref_mask_area_fraction']:5.2f} {f(o['var_same_cells']):>22s} {f(o['ref']):>22s} {f(d):>22s} "
          f"{(d[3] if d[3] is not None else float('nan')):8.1e} {o['anomaly_correlation']:5.2f} {o['step_2011']:+6.3f}  {d[4]}")
