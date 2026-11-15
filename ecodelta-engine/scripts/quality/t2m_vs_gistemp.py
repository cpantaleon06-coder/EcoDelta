"""MERRA-2 t2m vs gridded GISTEMP v4 over the same 21 boxes and the SAME cells.

For each GISTEMP product (250 km land-only; 1200 km land+ocean), per region:
  mask  = engine fixed-mask rule (>= 95% of months valid) applied to GISTEMP in the box
  MERRA-2 and GISTEMP averaged over that mask (trendkit.fixed_mask_mean with the mask as region)
  both deseasonalized with the 2001-01..2025-09 monthly climatology; trendkit trend_report on each
  D = MERRA-2 - GISTEMP: engine compute.compare_pair (Sen + Mann-Kendall Yue-Wang)
  descriptive step at 2011-01 in D: OLS of D on [1, t, t>=2011] (no p-value)
Also the MERRA-2 full-box result (the exported one) for reference.
Usage (from ecodelta-engine/, ECODELTA_DATA_DIR set): t2m_vs_gistemp.py <out.json>
"""
import json, sys
import numpy as np, pandas as pd, xarray as xr
from trendkit import deseasonalize_monthly, fixed_mask_mean, trend_report
from trendkit.timeutil import decimal_year
from ecodelta_engine import config
from ecodelta_engine.compute import compare_pair
from ecodelta_engine.load import open_variable, read_manifest
from ecodelta_engine.regions import box_mask, load_regions

REF = str(config.DATA_DIR / "data" / "reference" / "gistemp") + "/"  # nasa-data/data/reference/gistemp/README
m2 = open_variable(config.DATA_DIR, read_manifest(config.DATA_DIR)["t2m"])
dates = m2.time.values
t = decimal_year(dates)
seg2 = pd.DatetimeIndex(dates) >= "2011-01-01"
X = np.column_stack([np.ones_like(t), t - t.mean(), seg2.astype(float)])
rule = (config.FIXED_MASK_MIN_VALID, config.FIXED_MASK_MAX_MISSING_WEIGHT)

def gis(name):
    g = xr.open_dataset(REF + name)["tempanomaly"].sel(time=slice("2001-01-01", "2025-09-30"))
    assert g.sizes["time"] == 297, g.sizes
    return g.assign_coords(time=dates).astype(float)

def trend(an):
    r = trend_report(an, dates, deseasonalize=False)
    return None if r["verdict"] == "insufficient data" else \
        [r["slope_per_decade"], r["ci_low_per_decade"], r["ci_high_per_decade"], r["pvalue"]]

out = {}
products = {"g250": gis("gistemp250_GHCNv4.nc"), "g1200": gis("gistemp1200_GHCNv4_ERSSTv5.nc")}
w = np.cos(np.deg2rad(m2.lat))
for r in load_regions():
    box = box_mask(r["box"], m2.lat.values, m2.lon.values)
    full, _ = fixed_mask_mean(m2, box, *rule)
    row = {"merra2_full_box": trend(deseasonalize_monthly(full.values, dates)[0])}
    for k, g in products.items():
        gs, info = fixed_mask_mean(g, box, *rule)
        row[k + "_mask_area_fraction"] = round(info["region_area_fraction"], 3)
        if info["n_cells"] == 0:
            row[k] = row[k + "_merra2_same_cells"] = row[k + "_diff"] = None
            continue
        ms, _ = fixed_mask_mean(m2, info["mask"], *rule)
        a = deseasonalize_monthly(ms.values, dates)[0]
        b = deseasonalize_monthly(gs.values, dates)[0]
        row[k] = trend(b)
        row[k + "_merra2_same_cells"] = trend(a)
        cp = compare_pair(a, b, dates)
        ok = np.isfinite(a - b)
        step = np.linalg.lstsq(X[ok], (a - b)[ok], rcond=None)[0][2]
        row[k + "_diff"] = [cp["difference_slope_per_decade"], *(cp["difference_ci_per_decade"] or [None, None]),
                            cp["pvalue"], cp["verdict"], round(float(step), 3)]
    out[r["id"]] = row
json.dump(out, open(sys.argv[1], "w"), indent=1, default=float)
f = lambda v: "      n/a       " if v is None else f"{v[0]:+.2f}[{v[1]:+.2f},{v[2]:+.2f}]"
print(f"{'region':24s} {'M2 box':>18s} | {'250 land':>5s} {'M2 same':>18s} {'GIS250':>18s} {'diff':>18s} {'p':>7s} {'step':>6s} | {'1200':>5s} {'M2 same':>18s} {'GIS1200':>18s} {'diff':>18s} {'p':>7s} {'step':>6s}")
for rid, o in out.items():
    s = f"{rid:24s} {f(o['merra2_full_box']):>18s} |"
    for k in ("g250", "g1200"):
        d = o[k + "_diff"]
        s += f" {o[k+'_mask_area_fraction']:5.2f} {f(o[k+'_merra2_same_cells']):>18s} {f(o[k]):>18s} {f(d):>18s} " + \
             (f"{d[3]:7.1e} {d[5]:+6.2f} |" if d and d[3] is not None else f"{'':7s} {'':6s} |")
    print(s)
