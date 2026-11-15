"""t2m regional series (engine fixed mask) split at the MERRA-2 stream change 300 -> 400 (2011-01).

Per region: trendkit trend_report on the full record and on each segment (deseasonalized with the
full-record climatology), plus a descriptive step: OLS of anomaly on [1, t, t>=2011-01] (no p-value:
OLS errors ignore autocorrelation). Also mean anomaly of the five MERRA2_401 months minus the mean of
the 400-stream months within 12 months of them.
"""
import json, sys
import numpy as np, pandas as pd
from trendkit import deseasonalize_monthly, fixed_mask_mean, trend_report
from trendkit.timeutil import decimal_year
from ecodelta_engine import config
from ecodelta_engine.load import open_variable, read_manifest
from ecodelta_engine.regions import box_mask, load_regions

root = config.DATA_DIR
da = open_variable(root, read_manifest(root)["t2m"])
dates = pd.DatetimeIndex(da.time.values)
t = decimal_year(da.time.values)
seg2 = dates >= "2011-01-01"
s401 = dates.strftime("%Y-%m").isin(["2020-09", "2021-06", "2021-07", "2021-08", "2021-09"])
near = (~s401) & (dates >= "2019-09-01") & (dates <= "2022-09-01")
out = []
for r in load_regions():
    series, _ = fixed_mask_mean(da, box_mask(r["box"], da.lat.values, da.lon.values),
                                config.FIXED_MASK_MIN_VALID, config.FIXED_MASK_MAX_MISSING_WEIGHT)
    an, _ = deseasonalize_monthly(series.values, da.time.values)
    rep = lambda m: trend_report(an[m], da.time.values[m], deseasonalize=False)
    full, a, b = rep(np.ones_like(seg2)), rep(~seg2), rep(seg2)
    X = np.column_stack([np.ones_like(t), t - t.mean(), seg2.astype(float)])
    coef = np.linalg.lstsq(X, an, rcond=None)[0]
    f = lambda x: [round(x["slope_per_decade"], 3), round(x["ci_low_per_decade"], 3), round(x["ci_high_per_decade"], 3), x["pvalue"]]
    out.append({"region": r["id"], "full": f(full), "s300_2001_2010": f(a), "s400_2011_2025": f(b),
                "ols_step_2011": round(coef[2], 3), "ols_slope_with_step": round(10 * coef[1], 3),
                "anom_401_minus_nearby_400": round(an[s401].mean() - an[near].mean(), 3)})
json.dump(out, open(sys.argv[1], "w"), indent=1)
print(f"{'region':26s} {'full':>22s} {'2001-2010 (300)':>24s} {'2011-2025 (400)':>24s} {'step':>6s} {'slope|step':>10s} {'401-400':>7s}")
for o in out:
    g = lambda v: f"{v[0]:+.3f} [{v[1]:+.2f},{v[2]:+.2f}]"
    print(f"{o['region']:26s} {g(o['full']):>22s} {g(o['s300_2001_2010']):>24s} {g(o['s400_2011_2025']):>24s} "
          f"{o['ols_step_2011']:+6.3f} {o['ols_slope_with_step']:+10.3f} {o['anom_401_minus_nearby_400']:+7.3f}")
