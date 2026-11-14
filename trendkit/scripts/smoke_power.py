"""Smoke test on real data: monthly 2 m air temperature (T2M) from the NASA POWER API.

Fetches one point (Mexico City by default), drops the annual aggregate the API
mixes into the monthly output (month "13"), turns the fill value into NaN, and
prints `trend_report`. No authentication needed.

Run: python scripts/smoke_power.py
"""

import json
import sys
import urllib.request

import numpy as np
import pandas as pd

from trendkit import trend_report

URL = ("https://power.larc.nasa.gov/api/temporal/monthly/point?parameters=T2M&community=RE"
       "&longitude=-99.1&latitude=19.4&start=1981&end=2025&format=JSON")


def fetch(url):
    with urllib.request.urlopen(url, timeout=90) as response:
        return json.load(response)


def monthly_series(payload, parameter="T2M"):
    """Return (dates, values, units) for the monthly entries of a POWER point response."""
    raw = payload["properties"]["parameter"][parameter]
    fill = payload.get("header", {}).get("fill_value", -999.0)
    monthly = {k: v for k, v in raw.items() if 1 <= int(k[4:]) <= 12}  # "YYYY13" is the annual value
    keys = sorted(monthly)
    dates = pd.to_datetime(keys, format="%Y%m")
    values = np.array([np.nan if monthly[k] == fill else monthly[k] for k in keys], dtype=float)
    units = payload.get("parameters", {}).get(parameter, {}).get("units")
    return dates, values, units, len(raw) - len(monthly)


def main():
    try:
        payload = fetch(URL)
    except OSError as err:
        sys.exit(f"Could not reach the NASA POWER API: {err}")
    dates, values, units, dropped = monthly_series(payload)
    lon, lat = payload["geometry"]["coordinates"][:2]
    print(f"NASA POWER T2M at lat {lat}, lon {lon}: {len(values)} monthly values "
          f"{dates[0]:%Y-%m} to {dates[-1]:%Y-%m}, {int(np.isnan(values).sum())} missing, "
          f"{dropped} annual aggregate entries dropped")
    print(json.dumps(trend_report(values, dates, units=units), indent=2))


if __name__ == "__main__":
    main()
