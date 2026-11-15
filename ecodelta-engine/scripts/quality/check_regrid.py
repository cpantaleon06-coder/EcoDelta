"""Raw vs regridded global mean for one nasa-data product, and the processed file at the same months.

Reuses nasa-data/scripts/build_coarse_grid.py `check` (refetches 3 months over OPeNDAP; needs ~/.netrc).
Run with the nasa-data venv, from nasa-data/:
  .venv/bin/python -I ../EcoDelta/ecodelta-engine/scripts/quality/check_regrid.py GLDAS evap runoff_surface soil_moisture_0_10cm
"""
import sys
sys.path.insert(0, "scripts")
import numpy as np, xarray as xr
import build_coarse_grid as b

prod, variables = sys.argv[1], sys.argv[2:]
for k in list(b.PRODUCTS):
    if k != prod:
        del b.PRODUCTS[k]
months = ["2001-01", "2013-07", "2025-09"]
b.check(months)
for v in variables:
    da = xr.open_dataset(f"data/processed/{v}.nc")[v]
    for m in months:
        g = da.sel(time=m).values.squeeze()
        print(f"processed {v:22} {m} global_mean={b.global_mean(g, b.TLAT, b.TLON):.4f} valid={int(np.isfinite(g).sum())}")
